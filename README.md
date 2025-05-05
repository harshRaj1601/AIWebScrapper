# Web Scraper - Flask App 🦑

This is a Flask-based version of the Web Scraper application. It allows you to scrape web content using AI models to extract structured data.

## Features

- **AI-Powered Scraping**: Use various AI models to extract data from websites
- **Field Extraction**: Specify what fields you want to extract
- **Pagination Support**: Extract data from multiple pages
- **Download Options**: Export results as JSON or CSV
- **Database Storage**: Save your scraped data to a database

## Installation

1. Clone the repository (if you haven't already)

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Install Playwright browsers:
   ```
   playwright install
   ```

4. Set up your environment variables in a `.env` file:
   ```
   DATABASE_URL=sqlite:///webscraped_data.db
   GEMINI_API_KEY=your_gemini_api_key
   OPENAI_API_KEY=your_openai_api_key
   ```

## Usage

1. Start the Flask application:
   ```
   python app.py
   ```

2. Open a web browser and navigate to `http://127.0.0.1:5000/`

3. Configure your scraping job:
   - Enter the URLs you want to scrape
   - Select the AI model to use
   - Enable scraping and specify fields to extract
   - Enable pagination if needed
   - Click the "LAUNCH" button to start scraping

4. View and download the results:
   - The scraped data will be displayed in a table
   - Use the download buttons to export as JSON or CSV
   - Pagination URLs will be shown if pagination was enabled

## Database Configuration

By default, the application uses SQLite. For production environments, you can use:

### PostgreSQL
```
DATABASE_URL=postgresql://username:password@localhost/dbname
```

### MySQL
```
DATABASE_URL=mysql+pymysql://username:password@localhost/dbname
```

## API Keys

The application requires API keys for the AI models:

- **Gemini**: Get your API key from [Google AI Studio](https://makersuite.google.com/)
- **OpenAI**: Get your API key from [OpenAI Platform](https://platform.openai.com/)

## License

This project uses the same license as the original Universal Web Scraper.

## Acknowledgements

This Flask application is a conversion of the original Streamlit-based Universal Web Scraper, maintaining all of its functionality. 
