# OpenAI Integration Setup

This document explains how to set up OpenAI LLM integration for both local development and DigitalOcean App Platform deployment.

## Features

The OpenAI integration adds two AI-powered features:

1. **Customer Insights**: AI analysis of customer behavior and purchasing patterns
2. **Recommendation Explanations**: AI-generated explanations for why certain products complement each other

## Local Development Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Get OpenAI API Key

1. Sign up at [OpenAI Platform](https://platform.openai.com/)
2. Go to [API Keys](https://platform.openai.com/api-keys)
3. Create a new API key
4. Copy the key (starts with `sk-`)

### 3. Create Environment File

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-actual-api-key-here

# Optional: Add organization ID if required (check https://platform.openai.com/account/org-settings)
# OPENAI_ORG_ID=org-your-organization-id-here

# Optional: Change the model (default is gpt-3.5-turbo)
# OPENAI_MODEL=gpt-4-turbo-preview
```

### 4. Run the Application

```bash
python app.py
```

The app will automatically detect the OpenAI configuration and enable AI features.

## DigitalOcean App Platform Deployment

### 1. Push Code to GitHub

Ensure your code is pushed to GitHub. The `.env` file will be ignored (it's in `.gitignore`).

### 2. Set Environment Variables in DigitalOcean

1. Go to your DigitalOcean App Platform dashboard
2. Select your app
3. Go to **Settings** > **App-Level Environment Variables**
4. Add the following variables:

   | Key | Value |
   |-----|-------|
   | `OPENAI_API_KEY` | `sk-your-actual-api-key-here` |
   | `OPENAI_ORG_ID` | `org-your-organization-id-here` (optional) |
   | `OPENAI_MODEL` | `gpt-3.5-turbo` (optional) |

### 3. Deploy

The app will automatically use the environment variables set in DigitalOcean App Platform.

## How It Works

### Environment Variable Priority

The app uses the following priority for configuration:

1. **DigitalOcean**: Environment variables set in App Platform
2. **Local**: Variables in `.env` file (local development only)
3. **System**: System environment variables

### Security Features

- API keys are never committed to GitHub (`.env` is in `.gitignore`)
- OpenAI client initialization is wrapped in try/catch for graceful degradation
- If OpenAI is not configured, the app continues to work without AI features
- Error handling prevents API failures from breaking the main application

### API Endpoints

The integration adds these new endpoints:

- `GET /api/customer_insights?customer_id=C0001` - Get AI insights for a customer
- `GET /api/recommendation_explanation?products=item1&products=item2` - Get AI explanation for recommendations
- `GET /api/openai_status` - Check if OpenAI is available

## Troubleshooting

### OpenAI Not Working Locally

1. Check your `.env` file exists and has the correct API key
2. Verify the API key is valid at [OpenAI Platform](https://platform.openai.com/api-keys)
3. Check the console for error messages
4. Ensure you have sufficient OpenAI credits

### OpenAI Not Working on DigitalOcean

1. Check App-Level Environment Variables are set correctly
2. Redeploy the app after setting environment variables
3. Check the application logs for error messages

### AI Features Not Appearing

The UI automatically hides AI components when OpenAI is not configured or available. This is expected behavior and allows the app to function normally without OpenAI.

## Cost Considerations

- The integration uses GPT-3.5-turbo by default (cost-effective)
- Each customer insight generates ~200 tokens
- Each recommendation explanation generates ~100 tokens
- Monitor usage at [OpenAI Platform](https://platform.openai.com/usage)

## Customization

You can modify the AI prompts in `openai_service.py`:

- `_build_customer_insights_prompt()` - Customer analysis prompts
- `_build_recommendations_prompt()` - Product recommendation prompts

To change the OpenAI model, set the `OPENAI_MODEL` environment variable to any supported model (e.g., `gpt-4`, `gpt-4-turbo-preview`).