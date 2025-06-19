import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
import time

# Configuration
API_BASE_URL = "http://localhost:8000"

# Page configuration
st.set_page_config(
    page_title="Project Analysis RAG System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .metric-card {
        background: white;
        padding: 1rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .project-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #e9ecef;
        margin-bottom: 1rem;
    }
    
    .task-completed {
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 4px;
    }
    
    .task-pending {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 4px;
    }
    
    .success-message {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #c3e6cb;
    }
    
    .error-message {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'current_project' not in st.session_state:
    st.session_state.current_project = None

class APIClient:
    def __init__(self, base_url: str, token: str = None):
        self.base_url = base_url
        self.token = token
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
    
    def signup(self, username: str, email: str, password: str) -> Dict:
        """Register a new user"""
        data = {
            "username": username,
            "email": email,
            "password": password
        }
        response = requests.post(f"{self.base_url}/auth/signup", json=data)
        return response.json(), response.status_code
    
    def login(self, username: str, password: str) -> Dict:
        """Login user"""
        data = {
            "username": username,
            "password": password
        }
        response = requests.post(f"{self.base_url}/auth/login", json=data)
        return response.json(), response.status_code
    
    def upload_document(self, file, project_name: str = None, daily_hours: int = 8, working_days: int = 5) -> Dict:
        """Upload and analyze document"""
        files = {"file": file}
        data = {
            "project_name": project_name if project_name else "",
            "daily_hours": daily_hours,
            "working_days_per_week": working_days
        }
        response = requests.post(
            f"{self.base_url}/projects/upload-docs",
            files=files,
            data=data,
            headers=self.headers
        )
        return response.json(), response.status_code
    
    def get_projects(self) -> List[Dict]:
        """Get user's projects"""
        response = requests.get(f"{self.base_url}/projects/my-projects", headers=self.headers)
        if response.status_code == 200:
            return response.json()
        return []
    
    def get_project_details(self, project_id: int) -> Dict:
        """Get detailed project information"""
        response = requests.get(f"{self.base_url}/projects/project/{project_id}", headers=self.headers)
        return response.json(), response.status_code
    
    def generate_daily_tasks(self, project_id: int, target_date: str, day_number: int, daily_hours: int = 8) -> Dict:
        """Generate daily tasks for a project"""
        data = {
            "project_id": project_id,
            "target_date": target_date,
            "day_number": day_number,
            "daily_hours": daily_hours
        }
        response = requests.post(
            f"{self.base_url}/projects/generate-daily-tasks",
            data=data,
            headers=self.headers
        )
        return response.json(), response.status_code
    
    def log_daily_tasks(self, project_id: int, day_number: int, completed_tasks: List[Dict]) -> Dict:
        """Log completed daily tasks"""
        data = {
            "project_id": project_id,
            "day_number": day_number,
            "completed_tasks": completed_tasks
        }
        response = requests.post(
            f"{self.base_url}/projects/log-daily-tasks",
            json=data,
            headers=self.headers
        )
        return response.json(), response.status_code
    
    def get_daily_log(self, project_id: int, day_number: int) -> Dict:
        """Get daily log for a project"""
        params = {"project_id": project_id, "day_number": day_number}
        response = requests.get(f"{self.base_url}/projects/daily-log", params=params, headers=self.headers)
        return response.json(), response.status_code

def show_auth_page():
    """Display authentication page"""
    st.markdown('<div class="main-header"><h1>🚀 Project Analysis RAG System</h1><p>Intelligent Project Planning & Task Management</p></div>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_btn = st.form_submit_button("Login", use_container_width=True)
            
            if login_btn:
                if username and password:
                    api_client = APIClient(API_BASE_URL)
                    result, status_code = api_client.login(username, password)
                    
                    if status_code == 200:
                        st.session_state.authenticated = True
                        st.session_state.user_data = result["user"]
                        st.session_state.access_token = result["access_token"]
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {result.get('detail', 'Unknown error')}")
                else:
                    st.error("Please fill in all fields")
    
    with tab2:
        st.subheader("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Username")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            signup_btn = st.form_submit_button("Sign Up", use_container_width=True)
            
            if signup_btn:
                if new_username and new_email and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("Passwords do not match")
                    else:
                        api_client = APIClient(API_BASE_URL)
                        result, status_code = api_client.signup(new_username, new_email, new_password)
                        
                        if status_code == 200:
                            st.success("Account created successfully! Please login.")
                        else:
                            st.error(f"Signup failed: {result.get('detail', 'Unknown error')}")
                else:
                    st.error("Please fill in all fields")

def show_dashboard():
    """Display main dashboard"""
    api_client = APIClient(API_BASE_URL, st.session_state.access_token)
    
    # Header
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<div class="main-header"><h1>Welcome back, {st.session_state.user_data["username"]}! 👋</h1></div>', unsafe_allow_html=True)
    with col2:
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_data = None
            st.session_state.access_token = None
            st.session_state.current_project = None
            st.rerun()
    
    # Sidebar Navigation
    with st.sidebar:
        st.title("📊 Navigation")
        page = st.radio("Go to:", ["Dashboard", "Upload Document", "My Projects", "Daily Tasks"], index=0)
    
    if page == "Dashboard":
        show_dashboard_overview(api_client)
    elif page == "Upload Document":
        show_upload_page(api_client)
    elif page == "My Projects":
        show_projects_page(api_client)
    elif page == "Daily Tasks":
        show_daily_tasks_page(api_client)

def show_dashboard_overview(api_client: APIClient):
    """Show dashboard overview with metrics"""
    st.header("📈 Dashboard Overview")
    
    # Get projects for metrics
    projects = api_client.get_projects()
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Projects", len(projects), delta=None)
    
    with col2:
        active_projects = [p for p in projects if p.get('complexity_level') in ['Medium', 'High', 'Expert']]
        st.metric("Active Projects", len(active_projects), delta=None)
    
    with col3:
        if projects:
            avg_duration = sum([int(p.get('total_duration_weeks', '0').split()[0]) for p in projects if p.get('total_duration_weeks') and p.get('total_duration_weeks').split()[0].isdigit()]) / len(projects) if projects else 0
            st.metric("Avg Duration", f"{avg_duration:.1f} weeks", delta=None)
        else:
            st.metric("Avg Duration", "0 weeks", delta=None)
    
    with col4:
        complexity_counts = {}
        for p in projects:
            complexity = p.get('complexity_level', 'Unknown')
            complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
        most_common = max(complexity_counts.items(), key=lambda x: x[1])[0] if complexity_counts else "None"
        st.metric("Most Common Complexity", most_common, delta=None)
    
    # Recent Projects
    if projects:
        st.subheader("📋 Recent Projects")
        for project in projects[:3]:
            with st.container():
                st.markdown(f"""
                <div class="project-card">
                    <h4>{project['project_name']}</h4>
                    <p><strong>Summary:</strong> {project['project_summary'][:200]}...</p>
                    <p><strong>Complexity:</strong> {project['complexity_level']} | <strong>Duration:</strong> {project.get('total_duration_weeks', 'N/A')}</p>
                    <p><small>Created: {datetime.fromisoformat(project['created_at'].replace('Z', '+00:00')).strftime('%B %d, %Y')}</small></p>
                </div>
                """, unsafe_allow_html=True)
        
        # Project complexity distribution chart
        if len(projects) > 1:
            st.subheader("📊 Project Complexity Distribution")
            complexity_data = {}
            for project in projects:
                complexity = project.get('complexity_level', 'Unknown')
                complexity_data[complexity] = complexity_data.get(complexity, 0) + 1
            
            fig = px.pie(
                values=list(complexity_data.values()),
                names=list(complexity_data.keys()),
                title="Projects by Complexity Level"
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No projects yet. Upload your first document to get started!")

def show_upload_page(api_client: APIClient):
    """Show document upload page"""
    st.header("📄 Upload & Analyze Document")
    
    st.markdown("""
    Upload your project documentation (PDF or TXT) and our AI will analyze it to:
    - Extract project requirements and scope
    - Estimate time and resources needed
    - Generate detailed task breakdowns
    - Recommend technology stack
    """)
    
    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Choose a file", type=['pdf', 'txt'])
        
        col1, col2 = st.columns(2)
        with col1:
            project_name = st.text_input("Project Name (optional)", placeholder="Leave empty for auto-generation")
            daily_hours = st.number_input("Daily Working Hours", min_value=1, max_value=16, value=8)
        
        with col2:
            working_days = st.number_input("Working Days per Week", min_value=1, max_value=7, value=5)
        
        submit_btn = st.form_submit_button("Upload & Analyze", use_container_width=True)
        
        if submit_btn and uploaded_file is not None:
            with st.spinner("Processing document... This may take a moment."):
                try:
                    result, status_code = api_client.upload_document(
                        uploaded_file, project_name, daily_hours, working_days
                    )
                    
                    if status_code == 200 and result.get('success'):
                        st.success("Document uploaded and analyzed successfully!")
                        
                        # Display analysis results
                        if result.get('analysis'):
                            analysis = result['analysis']
                            
                            st.subheader("📊 Analysis Results")
                            
                            # Project overview
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.markdown(f"**Project Name:** {analysis['project_name']}")
                                st.markdown(f"**Summary:** {analysis['project_summary']}")
                                st.markdown(f"**Complexity:** {analysis['complexity_level']}")
                            
                            with col2:
                                if analysis.get('time_estimation'):
                                    est = analysis['time_estimation']
                                    st.metric("Total Duration", est.get('total_duration_weeks', 'N/A'))
                                    st.metric("Estimated Hours", est.get('total_hours_estimated', 'N/A'))
                            
                            # Scope and deliverables
                            st.subheader("🎯 Scope & Deliverables")
                            st.write(analysis['scope_and_deliverables'])
                            
                            # Developer tasks
                            if analysis.get('developer_tasks'):
                                st.subheader("✅ Developer Tasks")
                                for i, task in enumerate(analysis['developer_tasks'], 1):
                                    st.write(f"{i}. {task}")
                            
                            # Technology stack
                            if analysis.get('technology_stack'):
                                st.subheader("🛠️ Technology Stack")
                                tech_cols = st.columns(min(len(analysis['technology_stack']), 4))
                                for i, tech in enumerate(analysis['technology_stack']):
                                    with tech_cols[i % 4]:
                                        st.info(tech)
                            
                            # Time estimation details
                            if analysis.get('time_estimation'):
                                st.subheader("⏱️ Time Estimation Breakdown")
                                est = analysis['time_estimation']
                                
                                time_data = []
                                for key, value in est.items():
                                    if value and value != 'N/A':
                                        time_data.append({
                                            'Phase': key.replace('_', ' ').title(),
                                            'Duration': value
                                        })
                                
                                if time_data:
                                    df = pd.DataFrame(time_data)
                                    st.table(df)
                        
                        st.session_state.current_project = result.get('project_id')
                        
                    else:
                        st.error(f"Analysis failed: {result.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    st.error(f"Upload failed: {str(e)}")

def show_projects_page(api_client: APIClient):
    """Show projects page"""
    st.header("📁 My Projects")
    
    projects = api_client.get_projects()
    
    if not projects:
        st.info("No projects found. Upload a document to create your first project.")
        return
    
    # Search and filter
    col1, col2 = st.columns([2, 1])
    with col1:
        search_term = st.text_input("🔍 Search projects", placeholder="Enter project name or keyword")
    with col2:
        complexity_filter = st.selectbox("Filter by complexity", ["All", "Low", "Medium", "High", "Expert"])
    
    # Filter projects
    filtered_projects = projects
    if search_term:
        filtered_projects = [p for p in filtered_projects if search_term.lower() in p['project_name'].lower() or search_term.lower() in p['project_summary'].lower()]
    if complexity_filter != "All":
        filtered_projects = [p for p in filtered_projects if p.get('complexity_level') == complexity_filter]
    
    # Display projects
    for project in filtered_projects:
        with st.expander(f"📋 {project['project_name']} ({project['complexity_level']})", expanded=False):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown(f"**Summary:** {project['project_summary']}")
                st.markdown(f"**Duration:** {project.get('total_duration_weeks', 'N/A')}")
                st.markdown(f"**Created:** {datetime.fromisoformat(project['created_at'].replace('Z', '+00:00')).strftime('%B %d, %Y at %I:%M %p')}")
            
            with col2:
                if st.button(f"View Details", key=f"view_{project['id']}"):
                    show_project_details(api_client, project['id'])
                
                if st.button(f"Daily Tasks", key=f"tasks_{project['id']}"):
                    st.session_state.current_project = project['id']
                    st.rerun()

def show_project_details(api_client: APIClient, project_id: int):
    """Show detailed project information"""
    result, status_code = api_client.get_project_details(project_id)
    
    if status_code == 200:
        project = result
        
        st.subheader(f"📋 {project['project_name']}")
        
        # Basic info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Complexity", project['complexity_level'])
        with col2:
            st.metric("Duration", project.get('total_duration_weeks', 'N/A'))
        with col3:
            st.metric("Estimated Hours", project.get('total_hours_estimated', 'N/A'))
        
        # Detailed information tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Overview", "Tasks", "Technology", "Timeline"])
        
        with tab1:
            st.markdown("**Project Summary:**")
            st.write(project['project_summary'])
            
            st.markdown("**Scope & Deliverables:**")
            st.write(project['scope_and_deliverables'])
        
        with tab2:
            st.markdown("**Developer Tasks:**")
            for i, task in enumerate(project.get('developer_tasks', []), 1):
                st.write(f"{i}. {task}")
        
        with tab3:
            st.markdown("**Technology Stack:**")
            if project.get('technology_stack'):
                tech_cols = st.columns(min(len(project['technology_stack']), 3))
                for i, tech in enumerate(project['technology_stack']):
                    with tech_cols[i % 3]:
                        st.info(tech)
        
        with tab4:
            st.markdown("**Timeline Breakdown:**")
            timeline_data = {
                'Development Phase': project.get('development_phase', 'N/A'),
                'Testing Phase': project.get('testing_phase', 'N/A'),
                'Deployment Phase': project.get('deployment_phase', 'N/A'),
                'Buffer Included': project.get('buffer_included', 'N/A')
            }
            
            for phase, duration in timeline_data.items():
                st.write(f"**{phase}:** {duration}")

def show_daily_tasks_page(api_client: APIClient):
    """Show daily tasks management page"""
    st.header("📅 Daily Tasks Management")
    
    # Project selection
    projects = api_client.get_projects()
    if not projects:
        st.info("No projects found. Please create a project first.")
        return
    
    # Project selector
    project_options = {f"{p['project_name']} (ID: {p['id']})": p['id'] for p in projects}
    selected_project_key = st.selectbox("Select Project", list(project_options.keys()))
    selected_project_id = project_options[selected_project_key]
    
    if selected_project_id:
        st.session_state.current_project = selected_project_id
        
        # Date and day selection
        col1, col2, col3 = st.columns(3)
        with col1:
            target_date = st.date_input("Target Date", value=datetime.now().date())
        with col2:
            day_number = st.number_input("Day Number", min_value=1, value=1)
        with col3:
            daily_hours = st.number_input("Daily Hours", min_value=1, max_value=16, value=8)
        
        # Generate tasks button
        if st.button("Generate Daily Tasks", use_container_width=True):
            with st.spinner("Generating daily tasks..."):
                result, status_code = api_client.generate_daily_tasks(
                    selected_project_id, 
                    target_date.strftime("%Y-%m-%d"), 
                    day_number, 
                    daily_hours
                )
                
                if status_code == 200 and result.get('success'):
                    st.success("Daily tasks generated successfully!")
                    st.session_state[f"tasks_{selected_project_id}_{day_number}"] = result['daily_tasks']
                else:
                    st.error(f"Failed to generate tasks: {result.get('error', 'Unknown error')}")
        
        # Display and manage tasks
        task_key = f"tasks_{selected_project_id}_{day_number}"
        if task_key in st.session_state:
            daily_tasks = st.session_state[task_key]
            
            st.subheader(f"📋 Tasks for {daily_tasks['day']} ({daily_tasks['date']})")
            st.info(f"Planned Hours: {daily_tasks['planned_hours']} hours")
            
            # Task management
            completed_tasks = []
            
            with st.form(f"task_form_{day_number}"):
                st.markdown("**Mark completed tasks:**")
                
                for i, task in enumerate(daily_tasks['tasks']):
                    task_completed = st.checkbox(
                        f"{task['task']} ({task['estimated_hours']}h)",
                        key=f"task_{i}_{day_number}",
                        value=task.get('task_done', False)
                    )
                    
                    if task_completed:
                        completed_tasks.append({
                            'task': task['task'],
                            'estimated_hours': task['estimated_hours']
                        })
                
                submit_tasks = st.form_submit_button("Update Task Status", use_container_width=True)
                
                if submit_tasks:
                    result, status_code = api_client.log_daily_tasks(
                        selected_project_id, day_number, completed_tasks
                    )
                    
                    if status_code == 200 and result.get('success'):
                        st.success(f"Tasks updated! Completed: {result['completed_count']}, Remaining: {result['remaining_count']}")
                    else:
                        st.error(f"Failed to update tasks: {result.get('error', 'Unknown error')}")
        
        # Load existing daily log
        st.subheader("📊 Daily Log History")
        if st.button("Load Daily Log"):
            result, status_code = api_client.get_daily_log(selected_project_id, day_number)
            
            if status_code == 200 and result.get('success'):
                log_data = result['log']
                
                st.info(f"Date: {log_data['date']} | Planned Hours: {log_data['planned_hours']}")
                
                completed_count = sum(1 for task in log_data['tasks'] if task.get('task_done', False))
                total_count = len(log_data['tasks'])
                
                # Progress bar
                progress = completed_count / total_count if total_count > 0 else 0
                st.progress(progress)
                st.write(f"Progress: {completed_count}/{total_count} tasks completed ({progress:.1%})")
                
                # Task list with status
                for task in log_data['tasks']:
                    status = "✅" if task.get('task_done', False) else "⏳"
                    css_class = "task-completed" if task.get('task_done', False) else "task-pending"
                    
                    st.markdown(f"""
                    <div class="{css_class}">
                        {status} <strong>{task['task']}</strong> ({task['estimated_hours']}h)
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.warning("No daily log found for this day.")

# Main application logic
def main():
    if not st.session_state.authenticated:
        show_auth_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()