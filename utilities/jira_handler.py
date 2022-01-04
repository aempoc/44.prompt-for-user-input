from utilities.jira import JIRA
import json
#Prepare summary for ticket
class JiraHandler:
    def __init__(self, filename):
        self.filename = filename
    def prepSummary(self, issue_id):
        payload = json.dumps( {
                                "fields": {
                                    "project": {
                                    "key": "AA"
                                    },
                                    "summary": "Automated page creation/modification",
                                    "issuetype": {
                                    "name": "Task"
                                    },
                                    "description": {
                                    "type": "doc",
                                    "version": 1,
                                    "content": [
                                        {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                            "text": "Create the page through automation using attached details",
                                            "type": "text"
                                            }
                                        ]
                                        }
                                    ]
                                    }
                                }
                            })
        return payload

    def jiraConnect(self,user, pswd, host):
        jira = JIRA(host,user, pswd)
        issue_id = "AA"
        if issue_id:
            payload = self.prepSummary(issue_id)  
            new_issue = jira.create_issue(payload)
            #Attaches the *.txt files under /tmp directory.
            files = {
                        "file": (self.filename, open(self.filename,"rb"), "application-type")
                    }
            jira.add_attachment(new_issue['key'],files)
            #jira.add_comment(new_issue, 'Required files are Attached!')
        return str(new_issue['key'])

    def create_ticket(self):
        user = 'aem.poc.2021@gmail.com'
        pswd = '4riwCAaqb7bPmpGVWh7i318E'
        host = 'https://aempoc.atlassian.net/'
        return self.jiraConnect(user, pswd, host)
