from django.conf import settings
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpRequest, HttpResponse

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import google.auth.transport.requests
from googleapiclient.http import BatchHttpRequest


def _enrich_labels_with_counts(gmail, labels: list[dict]) -> tuple[list[dict], list[dict]]:
    """Return (user_labels, system_labels) with unread message counts for each label."""
    user_labels: list[dict] = []
    system_labels: list[dict] = []
    for lb in labels or []:
        label_id = lb.get("id")
        try:
            # Use label metadata which includes messagesUnread/messagesTotal
            detail = gmail.users().labels().get(userId="me", id=label_id).execute()
            lb["messagesTotal"] = detail.get("messagesUnread", 0)
        except Exception:
            lb["messagesTotal"] = 0
        (user_labels if (lb.get("type") == "user") else system_labels).append(lb)
    # Sort alphabetically by name for stable UI
    user_labels.sort(key=lambda x: (x.get("name") or "").lower())
    system_labels.sort(key=lambda x: (x.get("name") or "").lower())
    return user_labels, system_labels

def _client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def oauth_start(request: HttpRequest) -> HttpResponse:
    flow = Flow.from_client_config(_client_config(), scopes=settings.GOOGLE_OAUTH_SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    request.session["oauth_state"] = state
    return redirect(authorization_url)


def oauth_callback(request: HttpRequest) -> HttpResponse:
    state = request.session.get("oauth_state")
    flow = Flow.from_client_config(_client_config(), scopes=settings.GOOGLE_OAUTH_SCOPES, state=state)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    creds = flow.credentials
    
    # Get user profile to identify account
    gmail = build("gmail", "v1", credentials=creds)
    try:
        profile = gmail.users().getProfile(userId="me").execute()
        email = profile.get("emailAddress")
    except Exception:
        email = "unknown@gmail.com"
    
    # Create account ID from email
    account_id = email.replace("@", "_").replace(".", "_")
    
    # Initialize accounts session structure if not exists
    if "accounts" not in request.session:
        request.session["accounts"] = {}
    
    # Store account credentials and profile
    request.session["accounts"][account_id] = {
        "email": email,
        "credentials": {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or []),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        },
        "profile": profile
    }
    
    # Set as current account
    request.session["current_account"] = account_id
    
    # Clean up old single account structure
    request.session.pop("google_credentials", None)
    
    return redirect(reverse("mailops:dashboard"))


def _get_session_creds(request: HttpRequest) -> Credentials | None:
    accounts = request.session.get("accounts", {})
    current_account_id = request.session.get("current_account")
    
    if not current_account_id or current_account_id not in accounts:
        return None
    
    account_data = accounts[current_account_id]
    data = account_data.get("credentials")
    if not data:
        return None
    
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes") or [],
    )
    if creds and creds.expired and creds.refresh_token:
        request_adapter = google.auth.transport.requests.Request()
        creds.refresh(request_adapter)
        # update session
        request.session["accounts"][current_account_id]["credentials"]["token"] = creds.token
        request.session["accounts"][current_account_id]["credentials"]["expiry"] = (
            creds.expiry.isoformat() if creds.expiry else None
        )
    return creds


def _batch_fetch_metadata(gmail, message_ids: list[str]) -> list[dict]:
    results: list[dict] = []

    def _callback(request_id, response, exception):
        if exception is None and response is not None:
            headers = {h["name"]: h["value"] for h in response.get("payload", {}).get("headers", [])}
            results.append(
                {
                    "id": response.get("id"),
                    "snippet": response.get("snippet"),
                    "subject": headers.get("Subject"),
                    "from": headers.get("From"),
                    "to": headers.get("To"),
                    "date": headers.get("Date"),
                    "labelIds": response.get("labelIds", []),
                }
            )

    if not message_ids:
        return results

    # Gmail batch prefers up to 100 calls per batch
    for i in range(0, len(message_ids), 100):
        chunk = message_ids[i:i+100]
        # Use per-API batch endpoint (global batch is deprecated and returns 404)
        batch = BatchHttpRequest(callback=_callback, batch_uri='https://gmail.googleapis.com/batch/gmail/v1')
        for mid in chunk:
            batch.add(
                gmail.users().messages().get(
                    userId="me",
                    id=mid,
                    format="metadata",
                    metadataHeaders=["Subject", "From", "Date", "To"],
                )
            )
        try:
            batch.execute()
        except Exception:
            # Fallback: fetch sequentially if batch fails
            for mid in chunk:
                try:
                    response = gmail.users().messages().get(
                        userId="me",
                        id=mid,
                        format="metadata",
                        metadataHeaders=["Subject", "From", "Date", "To"],
                    ).execute()
                    _callback(None, response, None)
                except Exception:
                    continue
    # Keep original order (best-effort)
    order = {mid: idx for idx, mid in enumerate(message_ids)}
    results.sort(key=lambda m: order.get(m.get("id", ""), 0))
    return results


def dashboard(request: HttpRequest) -> HttpResponse:
    creds = _get_session_creds(request)
    if not creds:
        return render(request, "mailops/dashboard.html", {"connected": False})

    gmail = build("gmail", "v1", credentials=creds)
    
    # Get current account info
    accounts = request.session.get("accounts", {})
    current_account_id = request.session.get("current_account")
    current_account = accounts.get(current_account_id, {})
    
    # Labels
    labels_resp = gmail.users().labels().list(userId="me").execute()
    labels = labels_resp.get("labels", [])
    user_labels, system_labels = _enrich_labels_with_counts(gmail, labels)
    
    # Find Primary label (INBOX) and redirect to it by default
    primary_label_id = None
    for label in labels:
        if label.get("name", "").lower() == "inbox":
            primary_label_id = label.get("id")
            break
    
    # If Primary label exists, redirect to it
    if primary_label_id:
        return redirect(reverse("mailops:dashboard_by_label", args=[primary_label_id]))
    
    try:
        # Compute overall unread count from UNREAD system label metadata
        unread_label_id = None
        for lb in labels:
            if lb.get("id") == "UNREAD" or (lb.get("name") or "").upper() == "UNREAD":
                unread_label_id = lb.get("id")
                break
        if unread_label_id:
            unread_detail = gmail.users().labels().get(userId="me", id=unread_label_id).execute()
            # Some accounts expose messagesUnread; messagesTotal on UNREAD also reflects unread total
            all_messages_total = unread_detail.get("messagesUnread", unread_detail.get("messagesTotal", 0))
        else:
            all_messages_total = 0
    except Exception:
        all_messages_total = 0

    # Fetch only unread messages
    page_token = request.GET.get("pageToken")
    append_mode = request.GET.get("append") == "1"
    query = (request.GET.get("q") or "").strip()
    list_kwargs = {"userId": "me", "maxResults": 25, "labelIds": ["UNREAD"]}
    if page_token:
        list_kwargs["pageToken"] = page_token
    if query:
        list_kwargs["q"] = query
    msgs_resp = gmail.users().messages().list(**list_kwargs).execute()
    ids = [m["id"] for m in (msgs_resp.get("messages") or [])]
    messages = _batch_fetch_metadata(gmail, ids)
    next_token = msgs_resp.get("nextPageToken")

    # Accumulate messages in session when append is requested
    cache_key = "search__" + query if query else "inbox__all"
    cache = request.session.get("inbox_cache", {})
    if append_mode:
        existing = (cache.get(cache_key, {}).get("messages") or [])
        combined = existing + messages
        # prevent unbounded growth (keep latest 500)
        combined = combined[-500:]
        cache[cache_key] = {"messages": combined, "next": next_token}
        messages = combined
    else:
        cache[cache_key] = {"messages": messages, "next": next_token}
    request.session["inbox_cache"] = cache

    return render(
        request,
        "mailops/dashboard.html",
        {
            "connected": True,
            "current_account": current_account,
            "accounts": accounts,
            "labels_user": user_labels,
            "labels_system": system_labels,
            "messages": messages,
            "nextPageToken": next_token,
            "all_messages_total": all_messages_total,
            "query": query,
        },
    )


def logout_view(request: HttpRequest) -> HttpResponse:
    request.session.pop("accounts", None)
    request.session.pop("current_account", None)
    request.session.pop("oauth_state", None)
    request.session.pop("google_credentials", None)
    return redirect(reverse("mailops:dashboard"))


def account_management(request: HttpRequest) -> HttpResponse:
    accounts = request.session.get("accounts", {})
    current_account_id = request.session.get("current_account")
    return render(
        request,
        "mailops/account_management.html",
        {
            "accounts": accounts,
            "current_account_id": current_account_id,
        },
    )


def add_account(request: HttpRequest) -> HttpResponse:
    flow = Flow.from_client_config(_client_config(), scopes=settings.GOOGLE_OAUTH_SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    authorization_url, state = flow.authorization_url(
        access_type="offline", include_granted_scopes="true", prompt="consent"
    )
    request.session["oauth_state"] = state
    return redirect(authorization_url)


def switch_account(request: HttpRequest, account_id: str) -> HttpResponse:
    accounts = request.session.get("accounts", {})
    if account_id in accounts:
        request.session["current_account"] = account_id
    return redirect(reverse("mailops:dashboard"))


def remove_account(request: HttpRequest, account_id: str) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('mailops:account_management'))
    
    accounts = request.session.get("accounts", {})
    if account_id in accounts:
        del accounts[account_id]
        request.session["accounts"] = accounts
        
        # If we removed the current account, switch to another one
        current_account_id = request.session.get("current_account")
        if current_account_id == account_id:
            if accounts:
                request.session["current_account"] = list(accounts.keys())[0]
            else:
                request.session.pop("current_account", None)
    
    return redirect(reverse("mailops:account_management"))


def dashboard_by_label(request: HttpRequest, label_id: str) -> HttpResponse:
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    gmail = build("gmail", "v1", credentials=creds)
    
    # Get current account info
    accounts = request.session.get("accounts", {})
    current_account_id = request.session.get("current_account")
    current_account = accounts.get(current_account_id, {})
    
    labels_resp = gmail.users().labels().list(userId="me").execute()
    labels = labels_resp.get("labels", [])
    user_labels, system_labels = _enrich_labels_with_counts(gmail, labels)
    try:
        # Compute overall unread count from UNREAD system label metadata
        unread_label_id = None
        for lb in labels:
            if lb.get("id") == "UNREAD" or (lb.get("name") or "").upper() == "UNREAD":
                unread_label_id = lb.get("id")
                break
        if unread_label_id:
            unread_detail = gmail.users().labels().get(userId="me", id=unread_label_id).execute()
            all_messages_total = unread_detail.get("messagesUnread", unread_detail.get("messagesTotal", 0))
        else:
            all_messages_total = 0
    except Exception:
        all_messages_total = 0
    page_token = request.GET.get("pageToken")
    append_mode = request.GET.get("append") == "1"
    query = (request.GET.get("q") or "").strip()
    
    # Fetch only unread messages for this label
    list_kwargs = {"userId": "me", "labelIds": [label_id, "UNREAD"], "maxResults": 25}
    
    if page_token:
        list_kwargs["pageToken"] = page_token
    if query:
        list_kwargs["q"] = f"is:unread {query}"
    else:
        list_kwargs["q"] = "is:unread"
    
    msgs_resp = gmail.users().messages().list(**list_kwargs).execute()
    ids = [m["id"] for m in (msgs_resp.get("messages") or [])]
    messages = _batch_fetch_metadata(gmail, ids)
    next_token = msgs_resp.get("nextPageToken")

    # Accumulate per-label in session when append is requested
    cache_key = f"unread_label__{label_id}__{query}" if query else f"unread_label__{label_id}"
    cache = request.session.get("inbox_cache", {})
    if append_mode:
        existing = (cache.get(cache_key, {}).get("messages") or [])
        combined = existing + messages
        combined = combined[-500:]
        cache[cache_key] = {"messages": combined, "next": next_token}
        messages = combined
    else:
        cache[cache_key] = {"messages": messages, "next": next_token}
    request.session["inbox_cache"] = cache
    is_scrape = False
    for lb in (user_labels + system_labels):
        if lb.get("id") == label_id and (lb.get("name") or "").lower() == "scrape":
            is_scrape = True
            break
    return render(
        request,
        "mailops/dashboard.html",
        {
            "connected": True,
            "current_account": current_account,
            "accounts": accounts,
            "labels_user": user_labels,
            "labels_system": system_labels,
            "messages": messages,
            "active_label": label_id,
            "nextPageToken": next_token,
            "all_messages_total": all_messages_total,
            "is_scrape_label": is_scrape,
            "query": query,
        },
    )


def label_delete_all(request: HttpRequest, label_id: str) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('mailops:dashboard_by_label', args=[label_id]))
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    gmail = build("gmail", "v1", credentials=creds)
    # List messages for this label in pages and delete
    next_token = None
    try:
        while True:
            kwargs = {"userId": "me", "labelIds": [label_id], "maxResults": 500}
            if next_token:
                kwargs["pageToken"] = next_token
            resp = gmail.users().messages().list(**kwargs).execute()
            ids = [m["id"] for m in (resp.get("messages") or [])]
            for mid in ids:
                try:
                    gmail.users().messages().trash(userId='me', id=mid).execute()
                except Exception:
                    continue
            next_token = resp.get("nextPageToken")
            if not next_token:
                break
    except Exception:
        pass
    return redirect(reverse('mailops:dashboard_by_label', args=[label_id]))


def _extract_bodies(payload: dict) -> tuple[str, str]:
    import base64

    def _decode(data: str) -> str:
        try:
            return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        except Exception:
            return ''

    plain_text = ''
    html_text = ''

    def walk(part: dict):
        nonlocal plain_text, html_text
        if not part:
            return
        body = part.get('body', {})
        data = body.get('data')
        mime = part.get('mimeType', '')
        if data:
            decoded = _decode(data)
            if mime == 'text/html' and not html_text:
                html_text = decoded
            elif mime == 'text/plain' and not plain_text:
                plain_text = decoded
        for child in part.get('parts', []) or []:
            walk(child)

    walk(payload)
    # Fallbacks: if only one exists, copy into the other to avoid empty render
    if html_text and not plain_text:
        plain_text = ''
    if plain_text and not html_text:
        html_text = ''
    return plain_text, html_text


def message_detail(request: HttpRequest, message_id: str) -> HttpResponse:
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    gmail = build("gmail", "v1", credentials=creds)
    
    # Get current account info
    accounts = request.session.get("accounts", {})
    current_account_id = request.session.get("current_account")
    current_account = accounts.get(current_account_id, {})
    
    msg = gmail.users().messages().get(userId="me", id=message_id, format="full").execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    body_plain, body_html = _extract_bodies(msg.get('payload'))
    
    # Mark message as read by removing UNREAD label
    try:
        gmail.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]}
        ).execute()
    except Exception:
        pass  # Continue even if marking as read fails
    
    # Get all labels for label management
    labels_resp = gmail.users().labels().list(userId="me").execute()
    all_labels = labels_resp.get("labels", [])
    user_labels = [l for l in all_labels if l.get("type") == "user"]
    
    return render(
        request,
        "mailops/message_detail.html",
        {
            "current_account": current_account,
            "accounts": accounts,
            "message": {
                "id": message_id,
                "subject": headers.get("Subject"),
                "from": headers.get("From"),
                "to": headers.get("To"),
                "date": headers.get("Date"),
                "snippet": msg.get("snippet"),
                "labelIds": msg.get("labelIds", []),
                "body_text": body_plain,
                "body_html": body_html,
            },
            "user_labels": user_labels,
        },
    )


def message_delete(request: HttpRequest, message_id: str) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('mailops:message_detail', args=[message_id]))
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    gmail = build("gmail", "v1", credentials=creds)
    gmail.users().messages().trash(userId='me', id=message_id).execute()
    return redirect(reverse('mailops:dashboard'))


def add_labels_to_message(request: HttpRequest, message_id: str) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('mailops:message_detail', args=[message_id]))
    
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    
    gmail = build("gmail", "v1", credentials=creds)
    
    # Get current message labels
    try:
        msg = gmail.users().messages().get(userId="me", id=message_id, format="metadata").execute()
        current_label_ids = set(msg.get("labelIds", []))
    except Exception:
        current_label_ids = set()
    
    # Get selected labels from form
    selected_label_ids = set(request.POST.getlist('label_ids'))
    
    # Calculate labels to add and remove
    labels_to_add = selected_label_ids - current_label_ids
    labels_to_remove = current_label_ids - selected_label_ids
    
    # Add new labels
    if labels_to_add:
        try:
            gmail.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": list(labels_to_add)}
            ).execute()
        except Exception:
            pass  # Continue even if adding labels fails
    
    # Remove unselected labels
    if labels_to_remove:
        try:
            gmail.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": list(labels_to_remove)}
            ).execute()
        except Exception:
            pass  # Continue even if removing labels fails
    
    return redirect(reverse('mailops:message_detail', args=[message_id]))


def remove_labels_from_message(request: HttpRequest, message_id: str) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('mailops:message_detail', args=[message_id]))
    
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    
    gmail = build("gmail", "v1", credentials=creds)
    label_ids = request.POST.getlist('label_ids')
    
    if label_ids:
        try:
            gmail.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": label_ids}
            ).execute()
        except Exception:
            pass  # Continue even if removing labels fails
    
    return redirect(reverse('mailops:message_detail', args=[message_id]))


def create_label(request: HttpRequest) -> HttpResponse:
    if request.method != 'POST':
        return redirect(reverse('mailops:dashboard'))
    
    creds = _get_session_creds(request)
    if not creds:
        return redirect(reverse("mailops:dashboard"))
    
    gmail = build("gmail", "v1", credentials=creds)
    label_name = request.POST.get('label_name', '').strip()
    
    if label_name:
        try:
            gmail.users().labels().create(
                userId="me",
                body={"name": label_name}
            ).execute()
        except Exception:
            pass  # Continue even if creating label fails
    
    return redirect(reverse('mailops:dashboard'))

