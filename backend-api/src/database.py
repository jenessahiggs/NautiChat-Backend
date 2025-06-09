from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

############################################################
# User Database
############################################################



############################################################
# LLM: Conversation Database
############################################################

# Note: This file path is under the assumption that the db folder exists and that you are running fastapi dev main from the src folder.
CONVERSTATION_DATABASE_URL = "sqlite:///./../db/conversation.db"
conv_engine = create_engine(CONVERSTATION_DATABASE_URL)
ConvSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=conv_engine)
ConvBase = declarative_base()

# Return the db to use for llm routes
def get_conv_db():
    db = ConvSessionLocal()
    try:
        yield db
    finally:
        db.close()