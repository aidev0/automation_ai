workflow_env_vars = []

workflow_tech = [
    "google-sheets",
    "twilio",
    "gmail"
]

agents = [
    {
        "agent_label": "retrieve_leads_data",
        "env_vars": [],
        "agent_task": "Connects to Google Sheets to retrieve leads data including phone numbers and email addresses.",
        "agent_tech": ["google-sheets"]
    },
    {
        "agent_label": "call_lead_via_twilio",
        "env_vars": [],
        "agent_task": "Checks if a phone number is available for the lead and uses Twilio to make a call.",
        "agent_tech": ["twilio", "google-sheets"]
    },
    {
        "agent_label": "send_email_via_gmail",
        "env_vars": [],
        "agent_task": "Checks if an email address is available for the lead and sends an email using Gmail API.",
        "agent_tech": ["gmail", "google-sheets"]
    },
    {
        "agent_label": "compile_action_and_response_report",
        "env_vars": [],
        "agent_task": "Compiles a summary report of all actions taken and responses received from leads.",
        "agent_tech": []
    },
    {
        "agent_label": "send_briefing_email",
        "env_vars": [],
        "agent_task": "Sends a briefing email to you with details of the actions taken and the responses.",
        "agent_tech": ["gmail"]
    }
]