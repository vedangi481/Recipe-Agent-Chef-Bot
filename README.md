# 👨‍🍳 ChefBot — AI Recipe Preparation Agent

> **Intelligent recipe recommendations powered by IBM watsonx.ai Granite models with a RAG (Retrieval-Augmented Generation) pipeline over a local recipe knowledge base.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-green)](https://flask.palletsprojects.com)
[![IBM watsonx.ai](https://img.shields.io/badge/IBM-watsonx.ai-0f62fe)](https://dataplatform.cloud.ibm.com)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-0.5-orange)](https://chromadb.com)
[![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-purple)](https://getbootstrap.com)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🤖 **AI Recipe Chat** | Natural language recipe queries powered by IBM Granite |
| 🔍 **RAG Pipeline** | ChromaDB semantic search over 5 curated knowledge bases |
| 🥘 **Ingredient Matching** | Enter what you have — get ranked recipe suggestions |
| 🔄 **Substitution Engine** | Find alternatives for any ingredient with explanations |
| 🌿 **Dietary Filters** | Vegetarian, Vegan, Jain, Gluten-Free, Diabetic-Friendly, High-Protein, Low-Carb |
| 📊 **Nutrition Panel** | Real-time macro display (calories, protein, carbs, fat) |
| 🍚 **Leftover Management** | Minimize food waste with smart leftover recipe ideas |
| ⭐ **Favorites & History** | Save recipes and revisit previous sessions |
| 🌙 **Dark Mode** | Full dark/light theme toggle |
| 🇮🇳 **Hindi Support** | Respond in English, Hindi, or Hinglish |
| 📱 **Fully Responsive** | Mobile-first Bootstrap 5 layout |

---

## 🏗️ Architecture

```
ChefBot
├── app.py                    # Flask application, routes, session management
├── rag_pipeline.py           # ChromaDB RAG: document ingestion + retrieval
├── watsonx_client.py         # IBM Granite model client + AGENT_INSTRUCTIONS
│
├── knowledge_base/
│   ├── recipes/              # Indian & international recipes
│   ├── techniques/           # Cooking techniques (tadka, dum, blanching…)
│   ├── substitutions/        # Ingredient substitution guide
│   ├── nutrition/            # Nutritional information & food safety
│   └── dietary/              # Dietary recommendations (Vegan, Jain, Diabetic…)
│
├── data/
│   └── recipes_dataset.json  # Recipe cards dataset for UI
│
├── templates/
│   └── index.html            # Main UI (Bootstrap 5, Jinja2)
│
└── static/
    ├── css/style.css         # Custom CSS with dark mode
    └── js/app.js             # Frontend logic
```

**RAG Data Flow:**
```
User Query → Embeddings (sentence-transformers) → ChromaDB Semantic Search
         → Retrieved Context → IBM Granite Prompt → Generated Response
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- IBM Cloud account (free tier works)
- IBM watsonx.ai project

### 1. Clone & Install

```bash
# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example env file
copy .env.example .env   # Windows
cp .env.example .env     # Mac/Linux

# Edit .env with your IBM credentials
notepad .env             # Windows
nano .env                # Mac/Linux
```

Set these values in `.env`:
```env
IBM_API_KEY=your_ibm_cloud_api_key
IBM_PROJECT_ID=your_watsonx_project_id
WATSONX_URL=https://us-south.ml.cloud.ibm.com
GRANITE_MODEL_ID=ibm/granite-3-8b-instruct
```

> **Demo Mode:** If credentials are not set, the app runs in demo mode with pre-built responses — great for testing the UI!

### 3. Run the Application

```bash
python app.py
```

Open your browser at **http://localhost:5000**

---

## 🔑 Getting IBM watsonx.ai Credentials

### Step 1: Create IBM Cloud Account
1. Go to [cloud.ibm.com](https://cloud.ibm.com) → Sign up for free
2. Verify your email

### Step 2: Get Your API Key
1. Go to [IBM Cloud IAM → API Keys](https://cloud.ibm.com/iam/apikeys)
2. Click **Create an IBM Cloud API Key**
3. Copy the key (shown only once)

### Step 3: Create a watsonx.ai Project
1. Go to [watsonx.ai](https://dataplatform.cloud.ibm.com/wx/home)
2. Create a new project
3. Note your **Project ID** from the project settings

### Step 4: Choose Your Region
Use the URL for your nearest IBM Cloud region:
- US South: `https://us-south.ml.cloud.ibm.com`
- Germany:  `https://eu-de.ml.cloud.ibm.com`
- UK:       `https://eu-gb.ml.cloud.ibm.com`
- Japan:    `https://jp-tok.ml.cloud.ibm.com`
- Australia:`https://au-syd.ml.cloud.ibm.com`

---

## 🧠 Knowledge Base Structure

The RAG pipeline ingests 5 knowledge bases:

| Collection | Contents |
|---|---|
| `recipes` | 20+ Indian & international recipe texts with instructions, nutrition |
| `techniques` | Tadka, Dum, Blanching, Pressure cooking, Roti making |
| `substitutions` | Egg, butter, milk, paneer, ghee, flour, sugar substitutes |
| `nutrition` | Macronutrients, vitamins, food safety, calorie tables |
| `dietary` | Vegetarian, Vegan, Jain, Gluten-Free, Diabetic, High-Protein guides |

### Adding Custom Recipes
1. Add `.txt` files to the appropriate `knowledge_base/` subfolder
2. Use the format from existing files (see `knowledge_base/recipes/indian_recipes.txt`)
3. Reload the knowledge base: `POST /api/reload-kb`

---

## 💬 Example Queries

```
"I have potatoes, onions, tomatoes, and cheese. What can I cook?"
"Suggest a high-protein vegetarian dinner"
"Replace eggs in this recipe"
"Give me gluten-free breakfast ideas"
"I only have leftover rice and vegetables"
"Suggest a recipe under 20 minutes"
"Can I substitute butter with olive oil?"
"What recipes can I prepare with paneer and spinach?"
"मुझे आलू और प्याज से कोई recipe बताओ"
"High protein vegan dinner suggestions chahiye"
```

---

## 🤖 Customizing the Agent

The assistant's personality, response style, and safety guidelines are all in one place. Edit `AGENT_INSTRUCTIONS` in [`watsonx_client.py`](watsonx_client.py):

```python
AGENT_INSTRUCTIONS = """
You are ChefBot, an AI-powered Recipe Preparation Assistant ...
"""
```

Customize:
- **Personality**: Formal vs. casual tone
- **Language**: Add regional languages (Marathi, Gujarati, etc.)
- **Safety**: Additional allergen warnings
- **Response format**: Change the recipe card structure
- **Expertise**: Add regional cuisine specializations

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET`  | `/` | Main web interface |
| `POST` | `/api/chat` | Main AI chat with RAG |
| `POST` | `/api/substitution` | Ingredient substitution finder |
| `POST` | `/api/nutrition` | Nutrition analysis |
| `POST` | `/api/quick-recipes` | Ingredient-based recipe suggestions |
| `GET`  | `/api/history` | Get session chat history |
| `DELETE` | `/api/history` | Clear chat history |
| `GET`  | `/api/favorites` | Get saved recipes |
| `POST` | `/api/favorites` | Save a recipe |
| `DELETE` | `/api/favorites/<id>` | Remove a saved recipe |
| `GET`  | `/api/status` | Health check & RAG status |
| `POST` | `/api/reload-kb` | Reload knowledge base |

---

## ☁️ Deployment on IBM Cloud

### Using IBM Code Engine (Recommended)

```bash
# Install IBM Cloud CLI
# https://cloud.ibm.com/docs/cli

# Login
ibmcloud login

# Target Code Engine project
ibmcloud ce project select --name my-recipe-agent

# Deploy from source
ibmcloud ce app create \
  --name chefbot \
  --build-source . \
  --strategy buildpacks \
  --env-from-secret chefbot-secrets \
  --port 5000 \
  --min-scale 0 \
  --max-scale 2

# Create secrets from .env
ibmcloud ce secret create --name chefbot-secrets \
  --from-env-file .env
```

### Using Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]
```

```bash
docker build -t chefbot .
docker run -p 5000:5000 --env-file .env chefbot
```

### Production with Gunicorn

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 app:app
```

---

## 🔧 Troubleshooting

| Issue | Solution |
|---|---|
| Demo mode showing | Set `IBM_API_KEY` and `IBM_PROJECT_ID` in `.env` |
| ChromaDB slow start | First run downloads embedding model (~90MB). Subsequent starts are fast. |
| `sentence-transformers` error | Run `pip install sentence-transformers` separately |
| Port 5000 in use | Change `PORT=5001` in `.env` |
| Knowledge base not updating | Call `POST /api/reload-kb` or delete `.chroma_db/` folder |

---

## 📁 Project Structure

```
recipe AI Agent/
├── app.py                    # Flask entry point
├── rag_pipeline.py           # RAG with ChromaDB
├── watsonx_client.py         # IBM Granite AI client
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── README.md                 # This file
│
├── knowledge_base/
│   ├── recipes/
│   │   ├── indian_recipes.txt
│   │   └── international_recipes.txt
│   ├── techniques/
│   │   └── cooking_techniques.txt
│   ├── substitutions/
│   │   └── ingredient_substitutions.txt
│   ├── nutrition/
│   │   └── nutritional_guide.txt
│   └── dietary/
│       └── dietary_recommendations.txt
│
├── data/
│   └── recipes_dataset.json
│
├── templates/
│   └── index.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── app.js
│
└── .chroma_db/               # Auto-created: ChromaDB vector store
```

---

## 🤝 Contributing

1. Add new recipes to `knowledge_base/recipes/` as `.txt` files
2. Follow the format: Recipe name, ingredients, instructions, nutrition
3. Call `POST /api/reload-kb` to update the vector store
4. Test with the example queries listed above

---

## 📄 License

MIT License — feel free to use, modify, and deploy.

---

*Built with ❤️ using IBM watsonx.ai Granite, Flask, ChromaDB, and Bootstrap 5*
