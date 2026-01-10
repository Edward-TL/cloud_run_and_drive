# Dhelos Clean Plan Sells

Cloud Run service that receives Wix Plan Sales webhooks and stores data in Google Drive Excel files.

## Features

- Receives POST webhooks from Wix Pricing Plans API
- Flattens nested JSON data into single-level format
- Appends data to Excel file stored in Google Drive
- Auto-creates headers if Excel file is empty

## Project Structure

```
├── main.py              # Cloud Run entry point
├── helpers.py           # Helper functions (flat_dictionary, update_excel)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Container configuration
├── sample_payload.json  # Sample Wix webhook payload for testing
├── .env.example         # Environment variables template
├── .github/workflows/
│   └── deploy.yml       # CI/CD pipeline
└── tests/
    └── test_helpers.py  # Unit tests
```

## Local Development

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install pytest  # for testing
   ```

2. **Set environment variables:**
   ```bash
   export GOOGLE_DRIVE_FILE_ID=your-file-id
   export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
   ```

3. **Run locally:**
   ```bash
   functions-framework --target load_to_excel --debug
   ```

4. **Test with sample payload:**
   ```bash
   curl -X POST http://localhost:8080 \
     -H "Content-Type: application/json" \
     -d @sample_payload.json
   ```

## Deployment

### Prerequisites

1. Enable GCP APIs:
   ```bash
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com drive.googleapis.com
   ```

2. Create Artifact Registry repository:
   ```bash
   gcloud artifacts repositories create dhelos-functions \
     --repository-format=docker \
     --location=us-central1
   ```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | Google Cloud project ID |
| `GCP_SA_KEY` | Service account JSON key (base64 encoded) |
| `GOOGLE_DRIVE_FILE_ID` | Target Excel file ID in Google Drive |

### Manual Deploy

```bash
# Build and push
docker build -t us-central1-docker.pkg.dev/PROJECT_ID/dhelos-functions/dhelos-clean-plan-sells .
docker push us-central1-docker.pkg.dev/PROJECT_ID/dhelos-functions/dhelos-clean-plan-sells

# Deploy
gcloud run deploy dhelos-clean-plan-sells \
  --image us-central1-docker.pkg.dev/PROJECT_ID/dhelos-functions/dhelos-clean-plan-sells \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_DRIVE_FILE_ID=your-file-id"
```

## Testing

```bash
python -m pytest tests/test_helpers.py -v
```

## License

MIT License - see [LICENSE](LICENSE)
