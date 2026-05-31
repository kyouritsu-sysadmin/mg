# Electrical Panel Drawing Data Extractor

This project is a FastAPI and agent-based system designed to extract structured information from electrical cubicle panel drawings (PDF files). It leverages the `claude-agent-sdk` alongside Pydantic validation and an image-cropping tool to parse details from complex technical documents.

## Project Structure

*   `main.py`: Entrypoint for the FastAPI web application. Provides an HTML user interface to upload drawings, convert pages to preview images, and trigger processing.
*   `agent.py`: Orchestrates the AI agent workflow. It sets up a Model Context Protocol (MCP) server for image manipulation, constructs prompts, handles extraction queries, validates JSON outputs against schema boundaries, and saves the results.
*   `models.py`: Defines the Pydantic data schemas used for structured data extraction and validation (`ProjectInfo`, `CubicleInfo`, and `TransformerSpec`).
*   `utils.py`: Contains utility functions to convert PDF documents into high-resolution PNG images using PyMuPDF (`fitz`).
*   `tasks.py`: Defines structural blueprints for encapsulating extraction tasks.
*   `tools.py`: A placeholder for additional custom tool definitions.

## Key Features

1.  **FastAPI Web Interface**: Users can upload drawing files and preview them in the browser.
2.  **PDF-to-Image Conversion**: PyMuPDF automatically renders PDF pages into high-resolution PNG assets for visual analysis.
3.  **Adaptive Agent Tools**: Implements a `crop_region` tool as an MCP server. This allows the AI agent to request high-resolution sub-crops of dense drawing coordinates when specific text or symbols are too small to read at full page scale.
4.  **Structured Extraction & Validation**: Standardizes AI outputs into validated Pydantic structures. It retries extraction up to three times with feedback context if validation fails, saving finalized data in JSON format.
