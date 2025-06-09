# NautiChat-Backend

The backend provides endpoints to

- Generate responses with the LLM
- Authenticate / register users
- View previous responses from the LLM
- Provide feedback for an LLM response

The endpoints lead to a local SQLite database setup.
Prior to running any endpoints, ensure that a folder called "db" exists:
- backend-api\db\\*Some_Database_Name.db*

The backend also handles rate limiting

Install dependencies `pip install -r requirements.txt`  
Update dependencies `pip freeze > requirements.txt`  

Run with `fastapi dev main.py`  
Docs at `{server}/docs`  
