from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
import json
import os
import sys
import asyncio
import pandas as pd
from io import StringIO
import os
from datetime import datetime

# Import functions from the original project
sys.path.append("..")  # Add parent directory to path
from functions.scraper import scrape_urls
from functions.pagination import paginate_urls
from functions.markdown import fetch_and_store_markdowns
from services.assets import MODELS_USED
from functions.api_management import initialize_db

# Only use WindowsProactorEventLoopPolicy on Windows
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure value in production

# Make sure the database is initialized
db_initialized = False

# Add custom filters to Jinja environment
@app.template_filter('fromjson')
def fromjson(value):
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return {}

# Add now() function to Jinja environment
@app.context_processor
def utility_processor():
    def now():
        return datetime.now()
    return dict(now=now, models=MODELS_USED)

@app.route('/', methods=['GET'])
def index():
    global db_initialized
    
    if not db_initialized:
        db_initialized = initialize_db()
    
    # Pass the complete models dictionary to the template
    return render_template('index.html', models=MODELS_USED)

@app.route('/scrape', methods=['POST'])
def scrape():
    # Get form data
    urls = request.form.getlist('urls[]')
    fields = request.form.getlist('fields[]')
    model_selection = request.form.get('model_selection')
    use_pagination = request.form.get('use_pagination') == 'true'
    pagination_details = request.form.get('pagination_details', '')
    max_output_tokens = int(request.form.get('max_output_tokens', 2048))
    
    # Store in session
    session['urls'] = urls
    session['fields'] = fields
    session['model_selection'] = model_selection
    session['use_pagination'] = use_pagination
    session['pagination_details'] = pagination_details
    session['max_output_tokens'] = max_output_tokens
    
    # Process data
    try:
        # Fetch or reuse the markdown for each URL
        unique_names = fetch_and_store_markdowns(urls)
        session['unique_names'] = unique_names
        
        total_input_tokens = 0
        total_output_tokens = 0
        total_cost = 0
        all_data = []
        pagination_info = None
        
        # 1) Scraping logic
        if fields:
            in_tokens_s, out_tokens_s, cost_s, parsed_data = scrape_urls(
                unique_names,
                fields,
                model_selection,
                max_output_tokens=max_output_tokens
            )
            total_input_tokens += in_tokens_s
            total_output_tokens += out_tokens_s
            total_cost += cost_s
            
            # Process the parsed data
            processed_data = []
            for item in parsed_data:
                if isinstance(item, dict):
                    # If it's already a dictionary, keep it as is
                    processed_item = item
                elif isinstance(item, str):
                    # If it's a string, try to parse it as JSON
                    try:
                        processed_item = json.loads(item)
                        # Print out what was successfully parsed for debugging
                        print(f"Successfully parsed JSON string: {type(processed_item)}")
                    except json.JSONDecodeError:
                        # If not valid JSON, keep as string
                        processed_item = {"parsed_data": item}
                        print(f"Failed to parse as JSON, keeping as string")
                else:
                    # For any other type, convert to a dict
                    processed_item = {"parsed_data": item}
                    print(f"Non-string, non-dict item: {type(item)}")
                
                processed_data.append(processed_item)
            
            # Debug print to see the structure
            print("PROCESSED DATA STRUCTURE:", processed_data[:1])
            
            all_data = processed_data
            session['in_tokens_s'] = in_tokens_s
            session['out_tokens_s'] = out_tokens_s
            session['cost_s'] = cost_s
        
        # 2) Pagination logic
        if use_pagination:
            in_tokens_p, out_tokens_p, cost_p, page_results = paginate_urls(
                unique_names,
                model_selection,
                pagination_details,
                urls,
                max_output_tokens=max_output_tokens
            )
            total_input_tokens += in_tokens_p
            total_output_tokens += out_tokens_p
            total_cost += cost_p
            
            pagination_info = page_results
            session['in_tokens_p'] = in_tokens_p
            session['out_tokens_p'] = out_tokens_p
            session['cost_p'] = cost_p
        
        # Save results to session
        session['results'] = {
            'data': all_data,
            'input_tokens': total_input_tokens,
            'output_tokens': total_output_tokens,
            'total_cost': total_cost,
            'pagination_info': pagination_info
        }
        
        return jsonify({'status': 'success', 'message': 'Scraping completed successfully!'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'An error occurred during scraping: {str(e)}'})

@app.route('/results', methods=['GET'])
def results():
    # Get results from session
    results = session.get('results', None)
    
    if not results:
        return redirect(url_for('index'))
    
    return render_template('results.html', results=results)

@app.route('/download_json', methods=['GET'])
def download_json():
    results = session.get('results', None)
    
    if not results or not results.get('data'):
        print("No results data found for JSON download")
        return redirect(url_for('index'))
    
    try:
        print(f"Preparing JSON download with {len(results['data'])} items")
        json_data = json.dumps(
            results['data'],
            default=lambda o: o.dict() if hasattr(o, 'dict') else str(o),
            indent=4
        )
        
        # Create a StringIO object
        string_io = StringIO(json_data)
        string_io.seek(0)  # Ensure cursor is at the beginning
        
        # Return the file
        return send_file(
            string_io,
            mimetype='application/json',
            as_attachment=True,
            download_name='scraped_data.json'
        )
    except Exception as e:
        print(f"Error downloading JSON: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_csv', methods=['GET'])
def download_csv():
    results = session.get('results', None)
    
    if not results or not results.get('data'):
        print("No results data found for CSV download")
        return redirect(url_for('index'))
    
    try:
        # Convert all data to a single DataFrame
        all_listings = []
        print(f"Processing {len(results['data'])} items for CSV download")
        
        for data in results['data']:
            if isinstance(data, dict) and "parsed_data" in data:
                # Extract parsed_data if it exists
                parsed_data = data["parsed_data"]
                if isinstance(parsed_data, dict) and "listings" in parsed_data:
                    all_listings.extend(parsed_data["listings"])
                else:
                    all_listings.append(parsed_data)
            elif isinstance(data, dict) and "listings" in data:
                all_listings.extend(data["listings"])
            elif isinstance(data, str):
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, dict) and "listings" in parsed:
                        all_listings.extend(parsed["listings"])
                    else:
                        all_listings.append(parsed)
                except json.JSONDecodeError:
                    all_listings.append({"content": data})
            else:
                all_listings.append(data)
        
        print(f"Generated {len(all_listings)} listings for CSV")
        
        # Handle empty listings
        if not all_listings:
            all_listings = [{"empty": "No data available"}]
        
        # Convert to DataFrame
        combined_df = pd.DataFrame(all_listings)
        csv_data = combined_df.to_csv(index=False)
        
        # Create a StringIO object
        string_io = StringIO(csv_data)
        string_io.seek(0)  # Ensure cursor is at the beginning
        
        return send_file(
            string_io,
            mimetype='text/csv',
            as_attachment=True,
            download_name='scraped_data.csv'
        )
    except Exception as e:
        print(f"Error downloading CSV: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_pagination_csv', methods=['GET'])
def download_pagination_csv():
    results = session.get('results', None)
    
    if not results or not results.get('pagination_info'):
        print("No pagination info found for CSV download")
        return redirect(url_for('index'))
    
    try:
        # Process pagination info
        all_page_rows = []
        print(f"Processing {len(results['pagination_info'])} pagination items for CSV")
        
        for item in results['pagination_info']:
            if not isinstance(item, dict):
                continue
                
            if "pagination_data" in item:
                pag_obj = item["pagination_data"]
                
                # Convert if it's a Pydantic model
                if hasattr(pag_obj, "dict"):
                    pag_obj = pag_obj.model_dump()
                elif isinstance(pag_obj, str):
                    try:
                        pag_obj = json.loads(pag_obj)
                    except json.JSONDecodeError:
                        pass
                        
                item["pagination_data"] = pag_obj
            
            pd_obj = item["pagination_data"]
            
            if (
                isinstance(pd_obj, dict)
                and "page_urls" in pd_obj
                and isinstance(pd_obj["page_urls"], list)
            ):
                for page_url in pd_obj["page_urls"]:
                    row_dict = {"page_url": page_url}
                    all_page_rows.append(row_dict)
            else:
                row_dict = dict(item)
                all_page_rows.append(row_dict)
        
        print(f"Generated {len(all_page_rows)} page URLs for CSV")
        
        # Handle empty data
        if not all_page_rows:
            all_page_rows = [{"empty": "No pagination URLs available"}]
        
        pagination_df = pd.DataFrame(all_page_rows)
        csv_data = pagination_df.to_csv(index=False)
        
        # Create a StringIO object
        string_io = StringIO(csv_data)
        string_io.seek(0)  # Ensure cursor is at the beginning
        
        return send_file(
            string_io,
            mimetype='text/csv',
            as_attachment=True,
            download_name='pagination_urls.csv'
        )
    except Exception as e:
        print(f"Error downloading pagination CSV: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/download_pagination_json', methods=['GET'])
def download_pagination_json():
    results = session.get('results', None)
    
    if not results or not results.get('pagination_info'):
        print("No pagination info found for JSON download")
        return redirect(url_for('index'))
    
    try:
        # Process pagination info
        all_page_rows = []
        print(f"Processing {len(results['pagination_info'])} pagination items for JSON")
        
        for item in results['pagination_info']:
            if not isinstance(item, dict):
                continue
                
            if "pagination_data" in item:
                pag_obj = item["pagination_data"]
                
                # Convert if it's a Pydantic model
                if hasattr(pag_obj, "dict"):
                    pag_obj = pag_obj.model_dump()
                elif isinstance(pag_obj, str):
                    try:
                        pag_obj = json.loads(pag_obj)
                    except json.JSONDecodeError:
                        pass
                        
                item["pagination_data"] = pag_obj
            
            pd_obj = item["pagination_data"]
            
            if (
                isinstance(pd_obj, dict)
                and "page_urls" in pd_obj
                and isinstance(pd_obj["page_urls"], list)
            ):
                for page_url in pd_obj["page_urls"]:
                    row_dict = {"page_url": page_url}
                    all_page_rows.append(row_dict)
            else:
                row_dict = dict(item)
                all_page_rows.append(row_dict)
        
        print(f"Generated {len(all_page_rows)} page URLs for JSON")
        
        # Handle empty data
        if not all_page_rows:
            all_page_rows = [{"empty": "No pagination URLs available"}]
        
        json_data = json.dumps(all_page_rows, indent=4)
        
        # Create a StringIO object
        string_io = StringIO(json_data)
        string_io.seek(0)  # Ensure cursor is at the beginning
        
        return send_file(
            string_io,
            mimetype='application/json',
            as_attachment=True,
            download_name='pagination_urls.json'
        )
    except Exception as e:
        print(f"Error downloading pagination JSON: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/clear_results', methods=['POST'])
def clear_results():
    # Clear session data
    session.pop('results', None)
    session.pop('in_tokens_s', None)
    session.pop('out_tokens_s', None)
    session.pop('cost_s', None)
    session.pop('in_tokens_p', None)
    session.pop('out_tokens_p', None)
    session.pop('cost_p', None)
    
    return jsonify({'status': 'success'})

@app.route('/api_keys', methods=['POST'])
def update_api_keys():
    for model, required_keys in MODELS_USED.items():
        for key_name in required_keys:
            key_value = request.form.get(key_name)
            if key_value:
                os.environ[key_name] = key_value
    
    # Update DATABASE_URL if provided
    database_url = request.form.get('DATABASE_URL')
    if database_url:
        os.environ['DATABASE_URL'] = database_url
    
    return jsonify({'status': 'success', 'message': 'API keys updated successfully!'})

if __name__ == '__main__':
    app.run(debug=False) 