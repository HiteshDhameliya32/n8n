---
applyTo: '**'
---


# response rules
this are the rules which you will follow to give me responses 
if you done some edits then at last clearly state what you have done and what is still needs to be done and waiting for you conformation.
at last always add suggestions/improvments that can be done.
if you are asked for detaild info always provided detailed info.
if you are asked to answer in short then always give your answer in short.

# page creation/editing rules
this rules are for creating new or editing pages.
if tell you to make perticular page you have to make it while following my app's styling and theme.
use the components folder's file for any kind of component that you need like color, button, text and many more use them as you need. 
you should not use any thing outside of this components.
use same classes for any component needed.
do not hallucinate or make assumptions. if you are not clear then check the componets.
all new created page should follow my projects theme and layout.
most function should use ajex for reload free page updates.
if you successfully make page edits while following this rules write "made with rule of master"

# backend editing rules
this rules are only for backend related edits

first check my dal and bal files to see if any thing is usable
you have to follow reusability and maintainability.

follow my project structure
all imports at the top of file.
every view should use dal and bal layer effectively	
all business logic like data manipulation in bal and database logic like retrieving data in dal layer


method of approach
1. dal layer should only contains logic of CURD operations.
    always start with dal layer for any edits.

2. bal layer contains all business related logic like data manipulation or any data processing before giving to view.
    always use bal layer after dal layer, bal layer should only import dal layer.

3. view will handle rest of things, views should only use bal layer imports.
    always use views at last, views only use data provided by bal as it is

all imports should be placed at top of the file

# general rules
always think before acting for complex task.
use sequential-thinking Tool for better thinking. Break the task into clear steps before doing any work.

you should not hallucinate or make assumptions, feel free to ask first before continuing
your edits should be minimal and only related to request

use my dal and bal layer effectively.
paths- 
E:\code\projects\django\Weiboo\Bal - for business logic
E:\code\projects\django\Weiboo\Dal - for data access logic

follow my project structure

there should be no troubleshooting steps
you are free to check any file that you need for request
every edit should be in working and it should not break any existing functionality
maintain my projects visual with my already defined classes.
edits should follow my projects theme

there should be no visual changes every thing should be pixel perfect while editing code.
only change when it is required.

If something goes wrong, tell it:
Restart from the last successful step.

Do not assume missing details. If unclear, ask me first instead of guessing.
Never skip, merge, or reorder steps.
On error, stop and report — no auto-continuation.
Keep plan, execution, and summary clearly separated.

in every response add "you can relax but can't quit"