# Kayfa AI Agent

## Setup
1. `pip install -r requirements.txt`
2. Open `secret_config.py` and fill in:
   - `MONGO_URI`
   - `MONGO_DB_NAME`
   - `GROQ_API_KEY`
3. Put your logo file at: `assets/logo.png`
4. (Optional) Regenerate course data by running `generate_data.ipynb`, or edit `data/courses.csv` directly.
5. Run the app:
   ```
   streamlit run app.py
   ```

## Project structure
- `app.py` - Streamlit UI (entry point)
- `agent.py` - Groq LLM agent with function/tool calling
- `knowledge_base.py` - reads course data directly from `data/courses.csv` (no vector search)
- `database.py` - MongoDB chat storage (create, list, load, delete chats)
- `secret_config.py` - your credentials (Mongo URI, DB name, Groq API key)
- `generate_data.ipynb` - Faker-based synthetic course data generator
- `data/courses.csv` - the course catalog used by the agent
