DOMAIN = "nestor"

CONF_SERVICE_ACCOUNT_JSON = "service_account_json"
CONF_HOUSEHOLD_ID = "household_id"

UPDATE_INTERVAL_MINUTES = 3
DEFAULT_EXPIRY_THRESHOLD_DAYS = 3
CONF_EXPIRY_THRESHOLD_DAYS = "expiry_threshold_days"

FIRESTORE_BASE = (
    "https://firestore.googleapis.com/v1/projects/{project_id}"
    "/databases/(default)/documents"
)
GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"
FIRESTORE_SCOPE = "https://www.googleapis.com/auth/datastore"
