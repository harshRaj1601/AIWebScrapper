# pagination.py

import json
from typing import List, Dict
from services.assets import PROMPT_PAGINATION 
from functions.markdown import read_raw_data
from functions.api_management import get_database_session
from pydantic import BaseModel, Field
from typing import List
from pydantic import create_model
from functions.llm_calls import (call_llm_model)
from services.database import ScrapedData


class PaginationModel(BaseModel):
    page_urls: List[str]


def get_pagination_response_format():
    return PaginationModel


def create_dynamic_listing_model(field_names: List[str]):
    field_definitions = {field: (str, ...) for field in field_names}
    return create_model('DynamicListingModel', **field_definitions) 

def build_pagination_prompt(indications: str, url: str) -> str:
    # Base prompt
    prompt = PROMPT_PAGINATION + f"\nThe page being analyzed is: {url}\n"

    if indications.strip():
        prompt += (
            "These are the user's indications. Pay attention:\n"
            f"{indications}\n\n"
        )
    else:
        prompt += (
            "No special user indications. Just apply the pagination logic.\n\n"
        )
    # Finally append the actual markdown data
    return prompt


def save_pagination_data(unique_name: str, pagination_data):
    db = get_database_session()
    try:
        # if it's a pydantic object, convert to dict
        if hasattr(pagination_data, "dict"):
            pagination_data = pagination_data.dict()
        
        # parse if string
        if isinstance(pagination_data, str):
            try:
                pagination_data = json.loads(pagination_data)
            except json.JSONDecodeError:
                pagination_data = {"raw_text": pagination_data}
    
        # Find the record and update it
        record = db.query(ScrapedData).filter(ScrapedData.unique_name == unique_name).first()
        if record:
            record.pagination_data = pagination_data
            db.commit()
            MAGENTA = "\033[35m"
            RESET = "\033[0m" 
            print(f"{MAGENTA}INFO:Pagination data saved for {unique_name}{RESET}")
        else:
            print(f"No record found for unique_name {unique_name}")
    except Exception as e:
        db.rollback()
        print(f"Error saving pagination data: {e}")
    finally:
        db.close()

def paginate_urls(unique_names: List[str], selected_model: str, indication: str, urls:List[str], max_output_tokens=None):
    """
    For each unique_name, read raw_data, detect pagination, save results,
    accumulate cost usage, and return a final summary.
    
    Parameters:
        unique_names (List[str]): List of unique names for URLs.
        selected_model (str): The LLM model to use.
        indication (str): User instructions about pagination.
        urls (List[str]): Original URLs being processed.
        max_output_tokens (int, optional): Maximum number of output tokens (especially useful for Gemini API).
    """
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0
    pagination_results = []

    for uniq,current_url in zip(unique_names, urls):
        raw_data = read_raw_data(uniq)
        if not raw_data:
            print(f"No raw_data found for {uniq}, skipping pagination.")
            continue
        response_schema=get_pagination_response_format()
        full_indication=build_pagination_prompt(indication,current_url)
        pag_data, token_counts, cost = call_llm_model(
            raw_data, 
            response_schema,
            selected_model, 
            full_indication,
            max_output_tokens=max_output_tokens
        )

        # store
        save_pagination_data(uniq, pag_data)

        # accumulate cost
        
        total_input_tokens += token_counts["input_tokens"]
        total_output_tokens += token_counts["output_tokens"]
        total_cost += cost

        pagination_results.append({"unique_name": uniq,"pagination_data": pag_data})

    return total_input_tokens, total_output_tokens, total_cost, pagination_results
