# QualityPilot AI

Copilote IA de recherche documentaire et d’analyse de la qualité fournisseurs.

## Objectif

QualityPilot permet d’interroger des procédures qualité en langage naturel, de retrouver les passages pertinents avec une architecture RAG et de calculer des KPI fournisseurs grâce à des outils exposés par MCP.

## Fonctionnalités prévues

- ingestion de documents PDF et Markdown ;
- génération d’embeddings ;
- stockage vectoriel avec PostgreSQL et pgvector ;
- génération de réponses sourcées avec un LLM ;
- calcul du PPM et du taux de non-conformité ;
- serveur MCP exposant des outils métier ;
- agent ReAct capable de sélectionner les outils ;
- interface Streamlit ;
- mini-POC VLM pour l’analyse d’images ;
- tests et évaluation du retrieval.

## Stack technique

- Python 3.12
- FastAPI
- PostgreSQL
- pgvector
- Ollama
- MCP
- Streamlit
- Docker Compose
- Git

## Statut

Projet personnel en cours de développement.

### Étape actuelle

Initialisation de l’environnement et du dépôt Git.