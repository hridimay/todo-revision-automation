from msal import ConfidentialClientApplication
import requests
import json
import datetime, re
import random, time
import os

CLIENT_ID = os.getenv('CLIENT_ID')
TENANT_ID = os.getenv('TENANT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
AUTHORITY = "https://login.microsoftonline.com/consumers/"
SCOPES = ["Tasks.ReadWrite"]
REFRESH_TOKEN = os.getenv('REFRESH_TOKEN')


app = ConfidentialClientApplication(CLIENT_ID, client_credential=CLIENT_SECRET, authority=AUTHORITY)

# Access token global variable
access_token = ""
# Initialize counters
request_counter = 0
start_time = time.time()

def refresh_access_token():
    global access_token
    result = app.acquire_token_by_refresh_token(REFRESH_TOKEN, scopes=SCOPES)
    access_token = result['access_token']
    print("Access token refreshed ✓")

def safe_request(url, headers, method='get', data=None, max_retries=3):
    global request_counter
    for attempt in range(max_retries):
        request_counter += 1  # Increment request counter
        if method.lower() == 'get':
            response = requests.get(url, headers=headers)
        elif method.lower() == 'post':
            response = requests.post(url, headers=headers, data=data)
        elif method.lower() == 'patch':
            response = requests.patch(url, headers=headers, data=data)
        else:
            raise ValueError("Method not supported")

        if response.status_code == 429 or 500 <= response.status_code < 600:
            wait_time = (2 ** attempt) + random.random()
            print(f"Rate limited or server error. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            return response
    return None  # After all retries have failed


def extract_percentage(task_description):
    """Extracts the percentage value from the task description."""
    match = re.search(r'(\d+(\.\d+)?)%\sQuestions', task_description)
    if match:
        return float(match.group(1))
    else:
        return None

def get_revision_task_content(existing_tasks, updated_tasks):
    """Sorts tasks by 'x% Questions' in descriptions and generates the revision task content."""
    # Assign sort keys
    for task in updated_tasks:
        task['sort_key'] = extract_percentage(task.get('body', {}).get('content', '')) or float('inf')
    sorted_tasks = sorted(updated_tasks, key=lambda x: x['sort_key'])

    task_dict = {task['id']: task for task in existing_tasks if task['title'].lower() != 'revision'}
    for task in sorted_tasks:
        if task['title'].lower() != 'revision':
            task_dict[task['id']] = task

    content = ""
    for task in task_dict.values():
        content += f"Title: {task['title']}\n\n{task.get('body', {}).get('content', 'No description')}-----------------------------------------------------------------------\n\n"
    return content


def check_and_update_revision_task(tasks_response, task_lists, updated_after):
    global access_token  # Ensure we have access to the current access token
    list_tasks_map = {task_list['id']: [] for task_list in task_lists}

    for response in tasks_response.get('responses', []):
        list_id = response['id']
        updated_tasks = response.get('body', {}).get('value', [])
        list_tasks_map[list_id] = updated_tasks

    for list_id, updated_tasks in list_tasks_map.items():
        # Fetch existing "Revision" task, if it exists
        revision_task = None
        revision_task_content = ""
        url = f'https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = safe_request(url, headers=headers)
        if response and response.status_code == 200:
            tasks = response.json().get('value', [])
            for task in tasks:
                if task['title'].lower() == 'revision':
                    revision_task = task
                    revision_task_content = task.get('body', {}).get('content', "")
                    break

        # Parse existing tasks in the revision content
        existing_tasks = parse_revision_content(revision_task_content)

        # Generate updated content for the "Revision" task
        new_revision_content = get_revision_task_content(existing_tasks, updated_tasks)

        # Create or update the "Revision" task
        if revision_task:
            # Update existing "Revision" task
            update_revision_task_content(list_id, revision_task['id'], new_revision_content)
        else:
            # Create a new "Revision" task
            create_or_update_revision_task(list_id, "Revision", new_revision_content)

def parse_revision_content(content):
    """Parse the existing revision task content into a list of task dictionaries."""
    tasks = []
    task_parts = content.strip().split('\n\n')  # Split by double newline to get individual tasks
    for part in task_parts:
        if not part.strip():
            continue  # Skip empty parts
        task_info = {}
        lines = part.split('\n')
        for line in lines:
            if line.startswith('ID: '):
                task_info['id'] = line.split('ID: ')[1].strip()
            elif line.startswith('Title: '):
                task_info['title'] = line.split('Title: ')[1].strip()
            elif line.startswith('Description: '):
                task_info['description'] = line.split('Description: ')[1].strip()
        if 'id' in task_info:  # Ensure 'id' key exists before adding
            tasks.append(task_info)
    return tasks

def update_revision_task_content(list_id, task_id, content):
    """Update the content of an existing "Revision" task."""
    global access_token
    url = f'https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks/{task_id}'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    data = {'body': {'contentType': 'text', 'content': content}}
    response = safe_request(url, headers=headers, data=json.dumps(data), method='patch')
    if response and response.status_code in [200, 204]:
        print(f"'Revision' task updated successfully in list {list_id} ✓")
    else:
        print(f"Failed to update 'Revision' task in list {list_id}")

def create_or_update_revision_task(list_id, title, content):
    """Create a new "Revision" task or update if it exists."""
    global access_token
    url = f'https://graph.microsoft.com/v1.0/me/todo/lists/{list_id}/tasks'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    data = {'title': title, 'body': {'contentType': 'text', 'content': content}}
    response = safe_request(url, headers=headers, data=json.dumps(data), method='post')
    if response and response.status_code in [200, 201]:
        print(f"'Revision' task created or updated successfully in list {list_id} ✓")
    else:
        print(f"Failed to create or update 'Revision' task in list {list_id}")

def get_task_lists():
    refresh_access_token()
    url = 'https://graph.microsoft.com/v1.0/me/todo/lists'
    headers = {'Authorization': f'Bearer {access_token}'}
    response = safe_request(url, headers=headers)
    if response and response.status_code == 200:
        print("Fetched task lists ✓")
        task_lists = response.json()['value']
        filtered_task_lists = [task_list for task_list in task_lists if task_list['displayName'].lower() not in ['flagged emails', 'tasks']]
        return filtered_task_lists
    else:
        print("Failed to fetch task lists")
        return []

def prepare_batch_request_for_tasks(task_lists, updated_after):
    requests_data = []
    for task_list in task_lists:
        url = f"/me/todo/lists/{task_list['id']}/tasks?$filter=lastModifiedDateTime gt {updated_after}"
        requests_data.append({"id": task_list['id'], "method": "GET", "url": url})
    print("Prepared batch request for tasks ✓")
    return {"requests": requests_data}

def split_batch_request(batch_request, chunk_size=20):
    # Split the original request's 'requests' list into chunks
    request_chunks = [batch_request['requests'][i:i + chunk_size] for i in range(0, len(batch_request['requests']), chunk_size)]
    # Create a new batch request for each chunk
    return [{"requests": chunk} for chunk in request_chunks]

def process_batch_requests(url, headers, batch_requests):
    combined_response = {'responses': []}
    for batch_request in batch_requests:
        response = safe_request(url, headers=headers, data=json.dumps(batch_request), method='post')
        if response and response.status_code == 200:
            batch_response = response.json()
            combined_response['responses'].extend(batch_response.get('responses', []))
        else:
            print("Failed to process a batch request")
    return combined_response

def main():
    global start_time
    updated_after = (datetime.datetime.utcnow() - datetime.timedelta(days=720000)).isoformat() + 'Z'
    task_lists = get_task_lists()
    batch_request = prepare_batch_request_for_tasks(task_lists, updated_after)
    
    # Split the batch request into chunks of 20
    batch_requests = split_batch_request(batch_request, chunk_size=20)
    
    url = 'https://graph.microsoft.com/v1.0/$batch'
    headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
    
    # Process each chunked batch request and combine the responses
    combined_response = process_batch_requests(url, headers, batch_requests)
    
    if combined_response['responses']:
        check_and_update_revision_task(combined_response, task_lists, updated_after)
    else:
        print("Failed to fetch updated tasks")

    # Print stats
    end_time = time.time()
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    print(f"Number of requests made: {request_counter}")

if __name__ == '__main__':
    main()
