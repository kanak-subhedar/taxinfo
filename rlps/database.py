import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read the database connection string from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# Prevent app from starting if DATABASE_URL is not set
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# Create the SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for our models
Base = declarative_base()



