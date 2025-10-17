from flask import Flask, render_template, request, jsonify, flash, redirect, url_for, session
import requests
import os
import json
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')  # Change this in production

# Configuration from env
ALLOWED_EXTENSIONS = set(filter(None, [ext.strip().lower() for ext in os.getenv('ALLOWED_EXTENSIONS', 'png,jpg,jpeg,gif,bmp,webp').split(',')]))
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
PROMPT_TEXT = os.getenv('PROMPT_TEXT')
VENDOR = os.getenv('VENDOR')
PUBLISHED = os.getenv('PUBLISHED')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    # Get data from session if available
    response_data = session.pop('response_data', None)
    submitted_text = session.pop('submitted_text', None)
    submitted_filename = session.pop('submitted_filename', None)
    submitted_material_type = session.pop('submitted_material_type', None)
    submitted_product_type = session.pop('submitted_product_type', None)
    submitted_product_name = session.pop('submitted_product_name', None)
    submitted_price = session.pop('submitted_price', None)
    submitted_compare_price = session.pop('submitted_compare_price', None)
    submitted_color_options = session.pop('submitted_color_options', None)
    submitted_size_options = session.pop('submitted_size_options', None)
    success = session.pop('success', False)
    error = session.pop('error', None)
    
    return render_template('index.html', 
                         response_data=response_data,
                         submitted_text=submitted_text,
                         submitted_filename=submitted_filename,
                         submitted_material_type=submitted_material_type,
                         submitted_product_type=submitted_product_type,
                         submitted_product_name=submitted_product_name,
                         submitted_price=submitted_price,
                         submitted_compare_price=submitted_compare_price,
                         submitted_color_options=submitted_color_options,
                         submitted_size_options=submitted_size_options,
                         success=success,
                         error=error)

@app.route('/submit', methods=['POST'])
def submit_form():
    try:
        # Check if file is present
        if 'file' not in request.files:
            flash('No file selected')
            return render_template('index.html', error='No file selected')
        
        file = request.files['file']
        # prompt removed
        material_type = request.form.get('material_type', '').strip()
        product_type = request.form.get('product_type', '').strip()
        product_name = request.form.get('product_name', '').strip()
        price = request.form.get('price', '').strip()
        compare_price = request.form.get('compare_price', '').strip()
        color_options = request.form.get('color_options', '').strip()
        size_options = request.form.get('size_options', '').strip()
        
        # Validate inputs
        if file.filename == '':
            flash('No file selected')
            return render_template('index.html', error='No file selected')
        
        # prompt removed
        if not material_type:
            flash('Material type is required')
            return render_template('index.html', error='Material type is required')
        
        if not product_type:
            flash('Product type is required')
            return render_template('index.html', error='Product type is required')
        
        if not product_name:
            flash('Product name is required')
            return render_template('index.html', error='Product name is required')
        
        if not price:
            flash('Price is required')
            return render_template('index.html', error='Price is required')
        
        if not color_options:
            flash('Color options are required')
            return render_template('index.html', error='Color options are required')
        
        if not size_options:
            flash('Size options are required')
            return render_template('index.html', error='Size options are required')
        
        if not allowed_file(file.filename):
            flash('Invalid file type. Only images are allowed.')
            return render_template('index.html', error='Invalid file type. Only images are allowed.')
        
        # Get filename without saving
        filename = secure_filename(file.filename)
        
        # Convert price to float for validation
        try:
            price_float = float(price) if price else 0.0
        except ValueError:
            flash('Invalid price format')
            return render_template('index.html', error='Invalid price format')
        
        # Convert compare price to float if provided
        compare_price_float = None
        if compare_price:
            try:
                compare_price_float = float(compare_price)
            except ValueError:
                flash('Invalid compare price format')
                return render_template('index.html', error='Invalid compare price format')
        
        # Parse color and size options
        colors = [color.strip() for color in color_options.split(',') if color.strip()]
        sizes = [size.strip() for size in size_options.split(',') if size.strip()]
        
        if not colors:
            flash('At least one color option is required')
            return render_template('index.html', error='At least one color option is required')
        
        if not sizes:
            flash('At least one size option is required')
            return render_template('index.html', error='At least one size option is required')
        
        # Generate variants using Cartesian product (n^n formula)
        variants = []
        for color in colors:
            for size in sizes:
                # Generate SKU based on option1 + option2 + product name
                # Clean and abbreviate for SKU
                color_abbr = color.replace(' ', '').lower()[:3]
                size_abbr = size.replace(' ', '').lower()[:3]
                product_abbr = ''.join([word[0] for word in product_name.split()]).lower()[:3]
                sku = f"sku-{product_abbr}-{size_abbr}-{color_abbr}"
                
                variant = {
                    "option1": size,  # Size is option1
                    "option2": color,  # Color is option2
                    "sku": sku,
                    "grams": 300,  # Static field
                    "inventory_management": "shopify",  # Static field
                    "inventory_quantity": 15,  # Static field
                    "inventory_policy": "deny",  # Static field
                    "fulfillment_service": "manual",  # Static field
                    "price": price_float,
                    "compare_at_price": compare_price_float if compare_price_float else None,
                    "requires_shipping": True,  # Static field
                    "taxable": True  # Static field
                }
                variants.append(variant)
        
        # Create options structure
        options = [
            {"name": "Size", "values": sizes},
            {"name": "Color", "values": colors}
        ]

        # Debug: print parsed inputs and constructed options/variants
        try:
            print("DEBUG form -> material_type=", material_type,
                  " product_type=", product_type,
                  " product_name=", product_name,
                  " price=", price,
                  " compare_price=", compare_price,
                  " color_options=", color_options,
                  " size_options=", size_options)
            print("DEBUG options:", options)
            print("DEBUG variants count:", len(variants))
            if variants:
                print("DEBUG sample variant:", variants[0])
        except Exception as _:
            pass
        
        # Remove null fields from variants (e.g., compare_at_price when not provided)
        for v in variants:
            if v.get('compare_at_price') is None:
                del v['compare_at_price']

        # Prepare flat webhook form fields (multipart) with JSON strings for nested arrays
        webhook_data = {
            'material_type': material_type,
            'product_type': product_type,
            'product_name': product_name,
            'price': str(price_float),
            'vendor': VENDOR if VENDOR is not None else '',
            'published': str(PUBLISHED) if PUBLISHED is not None else '',
            'filename': filename,
            # send as JSON strings in form fields (not files)
            'options': json.dumps(options, ensure_ascii=False),
            'variants': json.dumps(variants, ensure_ascii=False)
        }
        # Debug: print flattened webhook fields for options/variants
        try:
            print("DEBUG webhook_data options:", webhook_data.get('options'))
            print("DEBUG webhook_data variants (first 500 chars):",
                  (webhook_data.get('variants') or '')[:500])
        except Exception as _:
            pass
        if compare_price_float is not None:
            webhook_data['compare_price'] = str(compare_price_float)
        if PROMPT_TEXT and PROMPT_TEXT.strip():
            webhook_data['text'] = PROMPT_TEXT.strip()
        
        # Send file and data to webhook as multipart/form-data
        # Determine content type based on file extension
        file_extension = filename.rsplit('.', 1)[1].lower() if '.' in filename else 'jpg'
        content_type_map = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'webp': 'image/webp'
        }
        content_type = content_type_map.get(file_extension, 'image/jpeg')
        
        print(webhook_data)

        try:
            # Reset file pointer to beginning and send file directly
            file.seek(0)
            files = {
                'file': (filename, file, content_type)
            }
            
            response = requests.post(
                WEBHOOK_URL,
                data=webhook_data,
                files=files,
                timeout=200
            )
            
            # Prepare response data
            try:
                # Try to parse JSON response and extract fields
                json_data = response.json()

                # Normalize to a single dict if array returned
                if isinstance(json_data, list) and len(json_data) > 0 and isinstance(json_data[0], dict):
                    product_data = json_data[0]
                elif isinstance(json_data, dict):
                    product_data = json_data
                else:
                    product_data = {}

                # Prepare dynamic fields
                text_fields = []  # simple string/number fields suitable for direct copy
                data_fields = []  # complex list/dict fields pretty-printed

                def add_text_field(key: str, label: str, value: str):
                    element_id = f"field-{key.replace(' ', '-').replace('_', '-')}-content"
                    text_fields.append({
                        'key': key,
                        'label': label,
                        'content': value,
                        'element_id': element_id
                    })

                # Prefer commonly expected fields first if available (title/description/tags)
                title_val = product_data.get('title')
                if isinstance(title_val, (str, int, float)) and str(title_val).strip():
                    add_text_field('title', 'Title', str(title_val))

                description_val = product_data.get('description')
                if isinstance(description_val, (str, int, float)) and str(description_val).strip():
                    add_text_field('description', 'Description', str(description_val))

                tags_val = product_data.get('tags')
                if isinstance(tags_val, (str, int, float)) and str(tags_val).strip():
                    add_text_field('tags', 'Tags', str(tags_val))

                # Handle bullet points from various key spellings
                bullet_points_data = (
                    product_data.get('bullet_points')
                    or product_data.get('bulletPoints')
                    or product_data.get('bullet points')
                )
                bullet_points_list = []
                if bullet_points_data is not None:
                    if isinstance(bullet_points_data, list):
                        bullet_points_list = [str(x) for x in bullet_points_data if str(x).strip()]
                        bullet_points_text = '\n'.join(bullet_points_list)
                    else:
                        bullet_points_text = str(bullet_points_data)
                        if bullet_points_text.strip():
                            bullet_points_list = [bullet_points_text]
                    if bullet_points_text.strip():
                        add_text_field('bullet-points', 'Bullet Points', bullet_points_text)

                # Extract html if present so template can preview
                html_field = product_data.get('html', '') if isinstance(product_data.get('html', ''), str) else ''

                # Add remaining fields dynamically
                handled_keys = {'title', 'description', 'tags', 'html', 'bullet_points', 'bulletPoints', 'bullet points'}
                for key, value in (product_data.items() if isinstance(product_data, dict) else []):
                    if key in handled_keys:
                        continue
                    # Text-like values
                    if isinstance(value, (str, int, float)):
                        val_str = str(value)
                        if val_str.strip():
                            # Create a nice label from key
                            label = ' '.join([w.capitalize() for w in key.replace('_', ' ').split()])
                            add_text_field(key, label, val_str)
                    # Complex values -> data fields
                    elif isinstance(value, (list, dict)):
                        try:
                            pretty = json.dumps(value, indent=2, ensure_ascii=False)
                        except Exception:
                            pretty = str(value)
                        element_id = f"field-{key.replace(' ', '-').replace('_', '-')}-content"
                        label = ' '.join([w.capitalize() for w in key.replace('_', ' ').split()])
                        data_fields.append({
                            'key': key,
                            'label': label,
                            'content_json': pretty,
                            'element_id': element_id
                        })

                parsed_data = {
                    'text_fields': text_fields,
                    'data_fields': data_fields,
                    'html': html_field,
                    'bullet_points_list': bullet_points_list,
                    'raw_json': json.dumps(json_data, indent=2, ensure_ascii=False)
                }
            except:
                # If not JSON, use raw text
                # If the webhook returned pure HTML/text, detect HTML and pass it through
                raw_text = response.text or ''
                html_field = ''
                # Basic detection for HTML content
                if isinstance(raw_text, str) and ('<' in raw_text and '>' in raw_text):
                    html_field = raw_text

                parsed_data = {
                    'text_fields': [],
                    'data_fields': [],
                    'html': html_field,
                    'bullet_points_list': [],
                    'raw_json': raw_text
                }
            
            response_data = {
                'status_code': response.status_code,
                'parsed_data': parsed_data,
                'headers': dict(response.headers),
                'success': response.status_code == 200
            }
            
            
            # Store response data in session and redirect to prevent resubmission on reload
            session['response_data'] = response_data
            # prompt removed
            session['submitted_filename'] = filename
            session['submitted_material_type'] = material_type
            session['submitted_product_type'] = product_type
            session['submitted_product_name'] = product_name
            session['submitted_price'] = price
            session['submitted_compare_price'] = compare_price
            session['submitted_color_options'] = color_options
            session['submitted_size_options'] = size_options
            session['success'] = True
            
            return redirect(url_for('index'))
            
        except requests.exceptions.RequestException as e:
            session['error'] = f'Webhook request failed: {str(e)}'
            return redirect(url_for('index'))
    
    except Exception as e:
        session['error'] = f'An error occurred: {str(e)}'
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
