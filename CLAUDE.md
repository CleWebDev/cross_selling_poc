# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Flask-based cross-selling recommendation POC for home improvement retail (styled after Lowe's). The application combines association rule mining with TensorFlow embeddings to provide intelligent product recommendations based on customer purchase history.

## Development Commands

### Setup and Dependencies
```bash
pip install -r requirements.txt
```

### Running the Application
```bash
python app.py
```
The app runs on `http://localhost:5000` in development mode.

### Data Generation and Model Training
```bash
# Generate synthetic data (customers, products, purchases)
python data_generation.py

# Train recommendation models (association rules + embeddings)
python model_train.py
```

### Production Deployment
```bash
gunicorn app:app
```

## Architecture Overview

### Core Components

**`app.py`** - Flask web server with 9 REST API endpoints for customer data and recommendations

**`recommend.py`** - Main recommendation engine implementing:
- Association rules (market basket analysis)
- TensorFlow embeddings for product similarity
- Room-based recommendations
- Hybrid scoring (70% confidence, 30% similarity)

**`model_train.py`** - ML training pipeline that generates:
- `assoc_rules.json` - Association rules from purchase baskets
- `embeddings.npy` - Product similarity embeddings

**`data_generation.py`** - Synthetic data generator creating realistic retail scenarios

### Data Flow

1. **Training**: Purchase data → Association rules + TensorFlow embeddings
2. **Inference**: Item selection → Hybrid recommendations (rules + similarity + business logic)
3. **API**: Frontend queries recommendations via REST endpoints

### Key Data Files

- **`/data/customers.csv`** - 150 synthetic customers with realistic profiles
- **`/data/products.csv`** - 85+ products (appliances, tools, accessories)
- **`/data/purchases.csv`** - Transaction-level purchase data
- **`/data/complements.json`** - Predefined product complement relationships
- **`/data/rooms.json`** - Room categorization for cross-selling logic

### Frontend Structure

**Single-page application** with professional Lowe's-inspired UI:
- Customer selection and purchase history
- Real-time product recommendations
- Invoice-based cross-selling suggestions

## Business Logic

### Recommendation Strategy
The system uses **hybrid recommendations** combining:
- **Association Rules**: Traditional market basket analysis (support/confidence)
- **Neural Embeddings**: TensorFlow cosine similarity
- **Business Rules**: Room-based filtering and product complements
- **Scoring**: Weighted combination prioritizing confidence over similarity

### Product Domains
- **25 main products**: Appliances, tools, outdoor equipment
- **60+ accessories**: Filters, warranties, installation kits
- **Room categories**: Kitchen, Laundry, Outdoor, Utility, General

## Development Notes

### Thread Safety
The recommendation engine uses thread-safe bootstrapping with global caching for production deployment.

### Model Loading
Models and data are loaded lazily on first API request to avoid startup delays.

### Data Generation
The synthetic data generator creates realistic purchase patterns with geographic consistency (Ohio-based customers) and logical product combinations.