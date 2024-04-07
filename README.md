# Study Revision Plan Maker

Study Revision Plan Maker is a Python script designed to help students and learners manage their study revision plans more effectively. Utilizing Microsoft's Graph API, it allows for the automated creation and updating of tasks within Microsoft To Do based on chapter revisions. This script is especially useful for organizing study tasks by chapters, tracking progress, and ensuring that all areas of study are covered.

## Features

- **Automated Task Management:** Create or update revision tasks in Microsoft To Do.
- **Custom Task Format:** Tasks are formatted with specific annotations for better organization.
    - **Redo**
    - **Doubt**
    - **Didn't Attempt**
    - **(/) Not done at once ❌**
    - **x% Questions ✅**
- **Efficient Revision Tracking:** Sorts tasks by percentage of questions done, helping you prioritize your study focus.

## Prerequisites

Before running this script, ensure you have the following:
- A Microsoft account with access to Microsoft To Do.
- Python 3.x installed on your system.
- The `requests` and `msal` Python packages installed.
- Registered an Azure AD application in the Microsoft identity platform with permissions to access Microsoft To Do (Tasks.ReadWrite).

## Setup

1. Clone this repository to your local machine.

    ```bash
    git clone <repository-url>
    ```

2. Install the required Python packages.

    ```bash
    pip install requests msal
    ```

3. Configure your environment variables. You'll need to set `CLIENT_ID`, `TENANT_ID`, `CLIENT_SECRET`, and `REFRESH_TOKEN` with your Azure AD application's details and your Microsoft account's refresh token.

    ```bash
    export CLIENT_ID='your_client_id_here'
    export TENANT_ID='your_tenant_id_here'
    export CLIENT_SECRET='your_client_secret_here'
    export REFRESH_TOKEN='your_refresh_token_here'
    ```

## Usage

To run the Study Revision Plan Maker, execute the script in your terminal.

```bash
python study_revision_plan_maker.py
