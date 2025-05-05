import streamlit as st
import os
from dotenv import load_dotenv
from services.assets import MODELS_USED
from services.database import get_db_session, initialize_database

load_dotenv(override=True)
def get_api_key(model):
    """
    Returns an API key for a given model by:
      1) Looking up the environment var name in MODELS_USED[model].
         (We assume there's exactly one item in that set.)
      2) Returning the key from st.session_state if present;
         otherwise from os.environ.
    """
    env_var_name = list(MODELS_USED[model])[0]  # e.g., "GEMINI_API_KEY"
    return st.session_state.get(env_var_name) or st.secrets.get(env_var_name)

def get_database_session():
    """Returns a SQLAlchemy database session."""
    try:
        return get_db_session()
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

def initialize_db():
    """Initialize the database if it hasn't been already."""
    try:
        if 'db_initialized' not in st.session_state:
            initialize_database()
            st.session_state['db_initialized'] = True
        return True
    except Exception as e:
        st.error(f"Database initialization error: {e}")
        return False
