import requests
import os
import re
import pandas as pd
import subprocess
from datetime import datetime, timezone, timedelta
import statistics

filecoin_authors = [
    "kaitlin-beegle",
    "jennijuju",
    "anorth",
    "arajasek",
    "stebalien",
    "ZenGround0",
    "raulk"
    "momack2",
    "Kubuxu",
    "luckyparadise",
    "steven004",
    "androowoo",
    "cryptonemo",
    "dkkapur",
    "irenegia",
    "vkalghatgi",
    "nicola",
    "jsoares",
    "nikkolasg",
    "hugomrdias",
    "whyrusleeping",
    "q9f",
    "CluEleSsUK",
    "willscott",
    "jnthnvctr",
    "daviddias",
    "fridrik01",
    "vesahc",
    "AxCortesCubero",
    "maciejwitowski",
    "johnnymatthews",
    "alexytsu",
    "DecentCr8",
    "gammazero",
    "ribasushi",
    "marten-seemann",

]
def incumbant_authors(authors):
    for author in filecoin_authors:
        if author.lower() in authors.lower():
            return True
    return False


def get_git_log_for_file(repo_path, file_path):
    # Change to the repository directory
    os.chdir(repo_path)

    # Execute the Git command to get the log for the file
    result = subprocess.run(['git', 'log', '--follow', '--pretty=format:%H %ai %an %s', file_path], 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            text=True)

    if result.returncode != 0:
        return []

    # Parse the output into a list of commits
    commits = result.stdout.splitlines()
    return commits

def author(repo_path, file_path, commit_hash):
    result = subprocess.run(['git', 'show', f'{commit_hash}:{file_path}'], 
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            cwd=repo_path)
    if result.returncode != 0:
        print("Error", result.stderr)
        return []
    
    lines = result.stdout.splitlines()
    for i in range(0,10):
        if "author" in lines[i].lower():
            return " ".join(lines[i].split(" ")[1:])
        
    return "Unknown author"

def is_final_at_commit(repo_path, file_path, commit_hash):
    # Execute the Git command to get the status of the file at the commit
    result = subprocess.run(['git', 'show', f'{commit_hash}:{file_path}'], 
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True, 
                                cwd=repo_path)

    if result.returncode != 0:
        #print("Error", result.stderr)
        return []

    # Parse the output into a list of status
    lines = result.stdout.splitlines()
    final_statuss = [
        "Final",
        "Deferred",
        "Superseded",
        "Accepted",
        "Rejected",
    ]

    status = "Unknown"
    for i in range(0,10):
        if "status" in lines[i]:
            status = lines[i].split(" ")[1:]
            break


    for fstatus in final_statuss:
        if fstatus in status:
            return (True, status)
    return (False, status)

def compute_statistics(durations):
    # Convert durations to seconds for calculations
    durations_in_seconds = [d.total_seconds() for d in durations]
    
    # Calculate average
    average_duration = sum(durations_in_seconds) / len(durations)
    average_duration = timedelta(seconds=average_duration)
    
    # Calculate median
    median_duration = timedelta(seconds=statistics.median(durations_in_seconds))
    
    # Calculate standard deviation
    std_dev_duration = statistics.stdev(durations_in_seconds)
    std_dev_duration = timedelta(seconds=std_dev_duration)
    
    # Calculate min and max
    min_duration = min(durations)
    max_duration = max(durations)
    
    # Calculate total duration
    total_duration = sum(durations, timedelta())
    
    return {
        'average': average_duration,
        'median': median_duration,
        'std_dev': std_dev_duration,
        'min': min_duration,
        'max': max_duration,
        'total': total_duration
    }

def get_github_pr_details(owner, repo, access_token):
    base_url = "https://api.github.com"
    headers = {
        "Authorization": f"token {access_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    prs = []
    # Get list of pull requests
    all_urls = []
    for i in range(1, 5):
        all_urls.append(f"{base_url}/repos/{owner}/{repo}/pulls?state=all&per_page=100&page={i}")

    for url in all_urls:
        prs_response = requests.get(url, headers=headers)
        newprs = prs_response.json()
        prs.extend(newprs)

    reviewed_prs = []

    times_to_first_review_nonfil = []
    times_to_first_review_fil = []
    fil_merges = 0
    nonfil_merges = 0
    total_fil = 0
    total_nonfil = 0
    unreviewed_merges_fil = 0
    unreviewed_merges_nonfil = 0

    approved_new_files_fil = 0
    rejected_new_files_fil = 0
    approved_new_files_nonfil = 0
    rejected_new_files_nonfil = 0

    for pr in prs:
        reviewed_pr = {}

        pr_number = pr['number']
        author = pr['user']['login']
        created = pr['created_at']
        # parse created into datetime object
        date_created = datetime.fromisoformat(created.replace("Z", "+00:00"))

        print("PR Number: ", pr_number)
        reviewed_pr["pr_number"] = pr_number
        print("Author: ", author)
        reviewed_pr["author"] = author
        print("Date Created: ", date_created)
        reviewed_pr["date_created"] = date_created.replace(tzinfo=None)

        # Get list of comments for the pull request
        comments_url = pr["review_comments_url"]
        comments_response = requests.get(comments_url, headers=headers)
        comments = comments_response.json()

        diff_url = pr["diff_url"]
        diff_response = requests.get(diff_url, headers=headers)
        diff = diff_response.text
        
        lines = diff.splitlines()
        # Finding the index of the line that starts with '---'
        new_fip = False
        try:
            index_of_target_line = next(i for i, line in enumerate(lines) if line.startswith('---'))
            info_after_dashes = lines[index_of_target_line].split('--- ')[1]
            if "/dev/null" in info_after_dashes:
                new_fip = True
        except StopIteration:
            pass
        reviewed_pr["new_fip"] = "Yes" if new_fip else "No"


        merge_date = pr['merged_at']

        if incumbant_authors(author):
            if merge_date and new_fip:
                approved_new_files_fil += 1
            elif not merge_date and new_fip:
                rejected_new_files_fil += 1
        else:
            if merge_date and new_fip:
                approved_new_files_nonfil += 1
            elif not merge_date and new_fip:
                rejected_new_files_nonfil += 1



        # Get the first comment
        if comments == []:
            first_comment = None
            commentor = None
            date_commented = None
        else:
            first_comment = comments[0]
            commentor = first_comment['user']['login']
            created = first_comment['created_at']
            # parse created into datetime object
            date_commented = datetime.fromisoformat(created.replace("Z", "+00:00"))

        print("First Commentor: ", commentor)
        reviewed_pr["commentor"] = commentor
        print("Date First Commented: ", date_commented)
        if date_commented == None:
            reviewed_pr["date_commented"] = None
            reviewed_pr["time_to_first_review"] = None
            print("Time to first review: ", None)
        else:
            reviewed_pr["date_commented"] = date_commented.replace(tzinfo=None)
            reviewed_pr["time_to_first_review"] = (date_commented - date_created)
            print("Time to first review", date_commented - date_created)
        print("Authored by FF, PL: ", "Yes" if incumbant_authors(author) else "No")
        reviewed_pr["authored_by_ff_pl"] = "Yes" if incumbant_authors(author) else "No"
        print("Merged: ", "Yes" if merge_date else "No")
        print("Merge Date: ", merge_date)
        reviewed_pr["merged"] = "Yes" if merge_date else "No"
        print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
        if incumbant_authors(author):
            if date_commented != None:
                times_to_first_review_fil.append(date_commented - date_created)
            if merge_date:
                fil_merges += 1
            if merge_date != None and date_commented == None:
                unreviewed_merges_fil += 1

            total_fil += 1
        else:
            if date_commented != None:
                times_to_first_review_nonfil.append(date_commented - date_created)
            if merge_date:
                nonfil_merges += 1
            if merge_date != None and date_commented == None:
                unreviewed_merges_nonfil += 1

            total_nonfil += 1
        reviewed_prs.append(reviewed_pr)

    nonfil_stats = compute_statistics(times_to_first_review_nonfil)
    fil_stats = compute_statistics(times_to_first_review_fil)
    print("Non-FF, PL Stats: ")
    print("Average: ", nonfil_stats["average"])
    print("Median: ", nonfil_stats["median"])
    print("Std Dev: ", nonfil_stats["std_dev"])
    print("Min: ", nonfil_stats["min"])
    print("Max: ", nonfil_stats["max"])
    print("Total: ", nonfil_stats["total"])
    print("Total amount of reviewed PR's: ", len(times_to_first_review_nonfil))
    print("Total amount of PR's: ", total_nonfil)
    print("Unreviewed PR's merged: ", unreviewed_merges_nonfil)
    print("New file PR's approved: ", approved_new_files_nonfil)
    print("New file PR's rejected: ", rejected_new_files_nonfil)
    print("Total amount of PR's merged: ", nonfil_merges)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")
    print("FF, PL Stats: ")
    print("Average: ", fil_stats["average"])
    print("Median: ", fil_stats["median"])
    print("Std Dev: ", fil_stats["std_dev"])
    print("Min: ", fil_stats["min"])
    print("Max: ", fil_stats["max"])
    print("Total: ", fil_stats["total"])
    print("Total amount of PR's reviewed: ", len(times_to_first_review_fil))
    print("Total amount of PR's: ", total_fil)
    print("Unreviewed PR's merged: ", unreviewed_merges_fil)
    print("New file PR's approved: ", approved_new_files_fil)
    print("New file PR's rejected: ", rejected_new_files_fil)
    print("Total amount of PR's merged: ", fil_merges)
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n")

    print("Total amount of PR's: ", total_fil + total_nonfil)

    return reviewed_prs


# Set your GitHub personal access token, repo owner, and repo name
token = input("Enter your GitHub personal access token: ")
owner = "filecoin-project"
repo = "FIPs"

pr_data = get_github_pr_details(owner, repo, token)

df = pd.DataFrame(pr_data)
df.to_excel("./prs.xlsx", index=False)

exit()

repo_path = "./FIPs"
file_path = "FIPS/fip-0058.md"
commits = get_git_log_for_file(repo_path, file_path)

commit_history = {}
available_fips = []
for i in range(1,100):
    if i < 10:
        num = f"000{i}"
    else:
        num = f"00{i}"
    commits = get_git_log_for_file(repo_path=repo_path, file_path=f"FIPS/fip-{num}.md")

    if commits == []:
        continue

    available_fips.append(num)
    # seperate commits with a space as a delimiter
    commits = [commit.split(" ", 4) for commit in commits]
    commit_history[i] = []
    # only get the first line in commits
    for j, commit in enumerate(commits):
        # convert time to datetime object
        year, month, day = map(int, commit[1].split('-'))

        hours, minutes, seconds = map(int, commit[2].split(':'))
        
        tz_offset = int(commit[3][:3]) * 60 + int(commit[3][3:5])
        tz = timezone(timedelta(minutes=tz_offset))
        
        commit_details = {
            "sha": commit[0],
            "datetime": datetime(year, month, day, hours, minutes, seconds, tzinfo=tz),
            "message": commit[4]
        }
        commit_history[i].append(commit_details)

#print(f"Available FIPs: {available_fips}")

acceptance_history = {}

for fip in available_fips:
    fip_history = commit_history[int(fip)]
    # Get the first commit
    first_commit = fip_history[len(fip_history) - 1]
    acceptance_history[int(fip)] = {}
    acceptance_history[int(fip)]["first_commit"] = first_commit["datetime"]
    acceptance_history[int(fip)]["last_commit"] = fip_history[0]["datetime"]
    # reverse the list to get the latest commit first
    fip_history.reverse()
    for commit in fip_history:
        res = is_final_at_commit(repo_path=repo_path, file_path=f"FIPS/fip-{fip}.md", commit_hash=commit["sha"])
        if res == []:
            continue
        accepted = res[0]
        status = res[1][0]

        if accepted:
            acceptance_history[int(fip)]["accepted"] = commit["datetime"]
            break
    # if the FIP is not accepted, then the last commit is the last update
    # if not accepted
    if not accepted: 
        acceptance_history[int(fip)]["accepted"] = status
total = 0
outsiders = []
excel_data = []
for fip in acceptance_history:
    print("FIP: ", fip)
    commit_sha = commit_history[fip][len(commit_history[fip]) - 1]["sha"]
    print("First commit: ", acceptance_history[fip]["first_commit"])
    print("Last commit", acceptance_history[fip]["last_commit"])
    if fip < 10:
        num = f"000{fip}"
    else:
        num = f"00{fip}"
    auth = author(repo_path=repo_path, file_path=f"FIPS/fip-{num}.md", commit_hash=commit_sha)
    print("Author: ", auth)
    if incumbant_authors(auth):
        total += 1
        print("Authored by Filecoin Foundation or Protocol Labs")
    else:
        outsiders.append(fip)
        print("Authored by outsiders")
        
    finality = acceptance_history[fip]["accepted"]
    # Check if finality is a datetime object
    print("Finality: ", finality)
    if type(finality) != str:
        print("Time to finality: ", finality - acceptance_history[fip]["first_commit"])

    excel_data.append({
        "FIP": fip,
        "First Commit": acceptance_history[fip]["first_commit"].replace(tzinfo=None),
        "Last Commit": acceptance_history[fip]["last_commit"].replace(tzinfo=None),
        "Author": auth,
        "Finality": finality if type(finality) == str else finality.replace(tzinfo=None),
        "Time to Finality": finality - acceptance_history[fip]["first_commit"] if type(finality) != str else "Not finalized",
        "Authored by FF, PL": "Yes" if incumbant_authors(auth) else "No"
    })
    
    print("~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")

df = pd.DataFrame(excel_data)
df.to_excel("/home/pluto/fip_data.xlsx", index=False)

print(f"{total} / {len(acceptance_history)} FIPs authored by Filecoin Foundation or Protocol Labs")
print(f"Outsiders: {outsiders}")

# for fip in available_fips:
#     print("FIP: ", fip)
#     print("First commit: ", acceptance_history[int(fip)]["first_commit"])
#     print("Accepted: ", acceptance_history[int(fip)]["accepted"])


# Convert the data into a flat structure for pandas
data = []
for file, commits in all_commits.items():
    for commit in commits:
        data.append({"File": file, "Commit SHA": commit["sha"], "Commit Date": commit["date"]})

df = pd.DataFrame(data)

# Save to Excel
df.to_excel("/path/to/save/output.xlsx", index=False)
