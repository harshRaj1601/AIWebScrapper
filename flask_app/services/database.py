from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

Base = declarative_base()

# Define the model for the scraped_data table
class ScrapedData(Base):
    __tablename__ = 'scraped_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    unique_name = Column(String(255), nullable=False, unique=True, index=True)
    url = Column(Text, nullable=True)
    raw_data = Column(Text, nullable=True)
    formatted_data = Column(JSON, nullable=True)
    pagination_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ScrapedData(id={self.id}, unique_name='{self.unique_name}')>"


# Create engine and session factory
def get_engine():
    """Get SQLAlchemy engine from environment variables or session state"""
    db_url = st.session_state.get('DATABASE_URL') or os.environ.get('DATABASE_URL')
    
    if not db_url:
        # Default to a local SQLite database if no URL is provided
        db_url = "sqlite:///webscraped_data.db"
    
    return create_engine(db_url)


def get_db_session():
    """Get a new SQLAlchemy database session"""
    if 'db_engine' not in st.session_state:
        st.session_state['db_engine'] = get_engine()
        
    # Create the tables if they don't exist
    Base.metadata.create_all(st.session_state['db_engine'])
    
    # Create a session
    Session = sessionmaker(bind=st.session_state['db_engine'])
    return Session()


def initialize_database():
    """Initialize the database, creating tables if needed"""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine 