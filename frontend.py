import streamlit as st
import requests
import json
from datetime import datetime
import os
from typing import Optional, Dict, Any

# Configure Streamlit page
st.set_page_config(
    page_title="Project Analysis System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API Configuration
API_BASE_URL = "http://localhost:8000"

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        margin-bottom: 2rem;
    }
    .project-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
        background-color: #f9f9f9;
    }
    .project-card:hover {
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        cursor: pointer;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
        margin: 0.5rem 0;
    }
</style>
""", unsafe_allow_html=True)

class APIClient:
    """Client for interacting with the FastAPI backend"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
    
    def signup(self, username: str, email: str, password: str) -> Dict[str, Any]:
        """Register a new user"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/signup",
                json={"username": username, "email": email, "password": password}
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def login(self, username: str, password: str) -> Dict[str, Any]:
        """Authenticate user"""
        try:
            response = requests.post(
                f"{self.base_url}/auth/login",
                json={"username": username, "password": password}
            )
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": response.json().get("detail", "Login failed")}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_info(self, token: str) -> Dict[str, Any]:
        """Get current user information"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.base_url}/auth/me", headers=headers)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Failed to get user info"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def upload_and_analyze(self, file, token: str, project_name: str = None, daily_hours: int = 8, working_days: int = 5) -> Dict[str, Any]:
        """Upload document and analyze project"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            files = {"file": file}
            data = {
                "daily_hours": daily_hours,
                "working_days_per_week": working_days
            }
            if project_name:
                data["project_name"] = project_name
            
            response = requests.post(
                f"{self.base_url}/projects/upload-docs",
                headers=headers,
                files=files,
                data=data
            )
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_user_projects(self, token: str) -> Dict[str, Any]:
        """Get all projects for the user"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.base_url}/projects/my-projects", headers=headers)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Failed to fetch projects"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_project_details(self, project_id: int, token: str) -> Dict[str, Any]:
        """Get detailed project information"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.get(f"{self.base_url}/projects/project/{project_id}", headers=headers)
            if response.status_code == 200:
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": "Failed to fetch project details"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def delete_project(self, project_id: int, token: str) -> Dict[str, Any]:
        """Delete a project"""
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.delete(f"{self.base_url}/projects/project/{project_id}", headers=headers)
            return {"success": response.status_code == 200, "data": response.json()}
        except Exception as e:
            return {"success": False, "error": str(e)}

# Initialize API client
api_client = APIClient(API_BASE_URL)

def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_token' not in st.session_state:
        st.session_state.user_token = None
    if 'user_info' not in st.session_state:
        st.session_state.user_info = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'login'
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None

def show_login_page():
    """Display login/signup page"""
    st.markdown('<h1 class="main-header">📊 Project Analysis System</h1>', unsafe_allow_html=True)
    
    # Create tabs for login and signup
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if username and password:
                    result = api_client.login(username, password)
                    if result["success"]:
                        st.session_state.authenticated = True
                        st.session_state.user_token = result["data"]["access_token"]
                        st.session_state.user_info = result["data"]["user"]
                        st.session_state.current_page = 'dashboard'
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(f"Login failed: {result.get('error', 'Unknown error')}")
                else:
                    st.error("Please enter both username and password")
    
    with tab2:
        st.subheader("Create New Account")
        
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_username")
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input("Password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            submit_signup = st.form_submit_button("Sign Up")
            
            if submit_signup:
                if new_username and new_email and new_password and confirm_password:
                    if new_password == confirm_password:
                        result = api_client.signup(new_username, new_email, new_password)
                        if result["success"]:
                            st.success("Account created successfully! Please login with your credentials.")
                        else:
                            st.error(f"Signup failed: {result.get('error', 'Unknown error')}")
                    else:
                        st.error("Passwords do not match")
                else:
                    st.error("Please fill all fields")

def show_sidebar():
    """Display sidebar navigation"""
    with st.sidebar:
        st.title("Navigation")
        
        if st.session_state.authenticated and st.session_state.user_info:
            st.success(f"Welcome, {st.session_state.user_info['username']}!")
            
            if st.button("🏠 Dashboard"):
                st.session_state.current_page = 'dashboard'
                st.session_state.selected_project = None
                st.rerun()
            
            if st.button("📤 Upload Document"):
                st.session_state.current_page = 'upload'
                st.rerun()
            
            if st.button("📋 My Projects"):
                st.session_state.current_page = 'projects'
                st.session_state.selected_project = None
                st.rerun()
            
            st.divider()
            
            if st.button("🚪 Logout"):
                st.session_state.authenticated = False
                st.session_state.user_token = None
                st.session_state.user_info = None
                st.session_state.current_page = 'login'
                st.session_state.selected_project = None
                st.rerun()

def show_dashboard():
    """Display main dashboard"""
    st.markdown('<h1 class="main-header">📊 Dashboard</h1>', unsafe_allow_html=True)
    
    # Get user projects
    projects_result = api_client.get_user_projects(st.session_state.user_token)
    
    if projects_result["success"]:
        projects = projects_result["data"]
        
        # Display stats
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Projects", len(projects))
        
        with col2:
            complexity_counts = {}
            for project in projects:
                # Check both analysis and direct project data
                analysis = project.get("analysis", {})
                complexity = analysis.get("complexity_level", project.get("complexity_level", "Unknown"))
                complexity_counts[complexity] = complexity_counts.get(complexity, 0) + 1
            most_common = max(complexity_counts.items(), key=lambda x: x[1])[0] if complexity_counts else "None"
            st.metric("Most Common Complexity", most_common)
        
        with col3:
            recent_projects = len([p for p in projects if p.get("created_at")])
            st.metric("Recent Projects", recent_projects)
        
        # Quick actions
        st.subheader("Quick Actions")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Upload New Document", use_container_width=True):
                st.session_state.current_page = 'upload'
                st.rerun()
        
        with col2:
            if st.button("📋 View All Projects", use_container_width=True):
                st.session_state.current_page = 'projects'
                st.rerun()
        
        # Recent projects
        if projects:
            st.subheader("Recent Projects")
            for project in projects[:3]:  # Show last 3 projects
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        # Get project name from analysis or fallback
                        analysis = project.get("analysis", {})
                        project_name = analysis.get("project_name", project.get("project_name", "Unnamed Project"))
                        complexity = analysis.get("complexity_level", project.get("complexity_level", "Unknown"))
                        
                        # Get duration from time estimation
                        time_estimation = analysis.get("time_estimation", {})
                        duration = time_estimation.get("total_duration_weeks", project.get("total_duration_weeks", "N/A"))
                        
                        st.write(f"**{project_name}**")
                        st.write(f"Complexity: {complexity}")
                        st.write(f"Duration: {duration} weeks" if duration != "N/A" else "Duration: N/A")
                    with col2:
                        if st.button("View", key=f"view_{project['id']}"):
                            st.session_state.selected_project = project['id']
                            st.session_state.current_page = 'project_detail'
                            st.rerun()
                    st.divider()
    else:
        st.error("Failed to load dashboard data")

def show_upload_page():
    """Display document upload page"""
    st.markdown('<h1 class="main-header">📤 Upload Document</h1>', unsafe_allow_html=True)
    
    with st.form("upload_form"):
        st.subheader("Upload Project Document")
        
        # File upload
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt'],
            help="Upload a PDF or TXT file containing project requirements"
        )
        
        # Project configuration
        col1, col2 = st.columns(2)
        
        with col1:
            project_name = st.text_input(
                "Project Name (Optional)",
                help="Leave empty to auto-generate based on document content"
            )
            daily_hours = st.number_input(
                "Daily Working Hours",
                min_value=1,
                max_value=16,
                value=8,
                help="Average number of hours worked per day"
            )
        
        with col2:
            working_days = st.number_input(
                "Working Days per Week",
                min_value=1,
                max_value=7,
                value=5,
                help="Number of working days per week"
            )
        
        submit_upload = st.form_submit_button("Upload and Analyze", use_container_width=True)
        
        if submit_upload:
            if uploaded_file is not None:
                with st.spinner("Uploading and analyzing document..."):
                    result = api_client.upload_and_analyze(
                        uploaded_file,
                        st.session_state.user_token,
                        project_name if project_name else None,
                        daily_hours,
                        working_days
                    )
                    
                    if result["success"]:
                        st.success("Document uploaded and analyzed successfully!")
                        st.session_state.current_page = 'projects'
                        st.rerun()
                    else:
                        st.error(f"Upload failed: {result.get('error', 'Unknown error')}")
            else:
                st.error("Please select a file to upload")

def show_projects_page():
    """Display all user projects"""
    st.markdown('<h1 class="main-header">📋 My Projects</h1>', unsafe_allow_html=True)
    
    # Get user projects
    projects_result = api_client.get_user_projects(st.session_state.user_token)
    
    if projects_result["success"]:
        projects = projects_result["data"]
        
        if not projects:
            st.info("No projects found. Upload a document to create your first project.")
            if st.button("📤 Upload Document"):
                st.session_state.current_page = 'upload'
                st.rerun()
        else:
            # Get unique complexity levels from both analysis and direct project data
            complexity_options = set()
            for project in projects:
                analysis = project.get("analysis", {})
                complexity = analysis.get("complexity_level", project.get("complexity_level", "Unknown"))
                complexity_options.add(complexity)
            
            # Filter and search
            col1, col2 = st.columns([2, 1])
            with col1:
                search_term = st.text_input("🔍 Search projects", placeholder="Enter project name...")
            with col2:
                complexity_filter = st.selectbox(
                    "Filter by Complexity",
                    ["All"] + list(complexity_options)
                )
            
            # Apply filters
            filtered_projects = projects
            if search_term:
                filtered_projects = []
                for p in projects:
                    analysis = p.get("analysis", {})
                    project_name = analysis.get("project_name", p.get("project_name", ""))
                    if search_term.lower() in project_name.lower():
                        filtered_projects.append(p)
            
            if complexity_filter != "All":
                temp_filtered = []
                for p in filtered_projects:
                    analysis = p.get("analysis", {})
                    complexity = analysis.get("complexity_level", p.get("complexity_level", "Unknown"))
                    if complexity == complexity_filter:
                        temp_filtered.append(p)
                filtered_projects = temp_filtered
            
            st.write(f"Showing {len(filtered_projects)} of {len(projects)} projects")
            
            # Display projects
            for project in filtered_projects:
                with st.container():
                    st.markdown('<div class="project-card">', unsafe_allow_html=True)
                    
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        # Get project details from analysis or fallback
                        analysis = project.get("analysis", {})
                        project_name = analysis.get("project_name", project.get("project_name", "Unnamed Project"))
                        complexity = analysis.get("complexity_level", project.get("complexity_level", "Unknown"))
                        
                        # Get duration from time estimation
                        time_estimation = analysis.get("time_estimation", {})
                        duration = time_estimation.get("total_duration_weeks", project.get("total_duration_weeks", "N/A"))
                        
                        st.subheader(project_name)
                        st.write(f"**Complexity:** {complexity}")
                        st.write(f"**Duration:** {duration} weeks" if duration != "N/A" else "**Duration:** N/A")
                        if project.get("created_at"):
                            st.write(f"**Created:** {project['created_at'][:10]}")
                    
                    with col2:
                        if st.button("👁️ View Details", key=f"view_detail_{project['id']}"):
                            st.session_state.selected_project = project['id']
                            st.session_state.current_page = 'project_detail'
                            st.rerun()
                    
                    with col3:
                        if st.button("🗑️ Delete", key=f"delete_{project['id']}"):
                            result = api_client.delete_project(project['id'], st.session_state.user_token)
                            if result["success"]:
                                st.success("Project deleted successfully!")
                                st.rerun()
                            else:
                                st.error("Failed to delete project")
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.divider()
    else:
        st.error("Failed to load projects")

def show_project_detail():
    """Display detailed project information"""
    if not st.session_state.selected_project:
        st.error("No project selected")
        return
    
    # Get project details
    result = api_client.get_project_details(
        st.session_state.selected_project,
        st.session_state.user_token
    )
    
    if result["success"]:
        project = result["data"]
        analysis = project.get("analysis", {})
        time_estimation = analysis.get("time_estimation", {})
        
        # Extract project name from analysis or fallback to project name
        project_name = analysis.get("project_name", project.get("project_name", "Project Details"))
        
        st.markdown(f'<h1 class="main-header">📋 {project_name}</h1>', 
                   unsafe_allow_html=True)
        
        # Back button
        if st.button("← Back to Projects"):
            st.session_state.current_page = 'projects'
            st.session_state.selected_project = None
            st.rerun()
        
        # Project overview
        st.subheader("Project Overview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            complexity = analysis.get("complexity_level", project.get("complexity_level", "Unknown"))
            st.metric("Complexity Level", complexity)
        with col2:
            duration = time_estimation.get("total_duration_weeks", project.get("total_duration_weeks", "N/A"))
            duration_text = f"{duration} weeks" if duration != "N/A" else "N/A"
            st.metric("Total Duration", duration_text)
        with col3:
            # Extract hours from time estimation
            total_hours = time_estimation.get("total_hours_estimated", 
                         time_estimation.get("base_hours_required", 
                         project.get("total_hours", "N/A")))
            if isinstance(total_hours, str) and "hours" in total_hours:
                total_hours = total_hours.split()[0]  # Extract number from "600 hours"
            hours_text = f"{total_hours} hours" if total_hours != "N/A" else "N/A"
            st.metric("Total Hours", hours_text)
        
        # Project Summary
        if analysis.get("project_summary"):
            st.subheader("Project Summary")
            st.write(analysis["project_summary"])
        
        # Scope and Deliverables
        if analysis.get("scope_and_deliverables"):
            st.subheader("Scope and Deliverables")
            st.write(analysis["scope_and_deliverables"])
        
        # Time Estimation Details
        if time_estimation:
            st.subheader("Time Estimation Breakdown")
            
            col1, col2 = st.columns(2)
            with col1:
                if time_estimation.get("base_hours_required"):
                    st.info(f"**Base Hours:** {time_estimation['base_hours_required']}")
                if time_estimation.get("total_hours_estimated"):
                    st.info(f"**Total Hours (with buffer):** {time_estimation['total_hours_estimated']}")
                if time_estimation.get("total_duration_days"):
                    st.info(f"**Total Days:** {time_estimation['total_duration_days']}")
            
            with col2:
                if time_estimation.get("development_phase"):
                    st.info(f"**Development Phase:** {time_estimation['development_phase']}")
                if time_estimation.get("testing_phase"):
                    st.info(f"**Testing Phase:** {time_estimation['testing_phase']}")
                if time_estimation.get("deployment_phase"):
                    st.info(f"**Deployment Phase:** {time_estimation['deployment_phase']}")
        
        # Developer Tasks
        if analysis.get("developer_tasks"):
            st.subheader("Developer Tasks")
            tasks = analysis["developer_tasks"]
            for i, task in enumerate(tasks, 1):
                with st.expander(f"Task {i}"):
                    st.write(task)
        
        # Technology Stack
        if analysis.get("technology_stack"):
            st.subheader("Technology Stack")
            tech_cols = st.columns(3)
            for i, tech in enumerate(analysis["technology_stack"]):
                with tech_cols[i % 3]:
                    st.info(tech)
        
        # Features (fallback for older data structure)
        if project.get("features"):
            st.subheader("Features")
            features = project["features"]
            for i, feature in enumerate(features, 1):
                with st.expander(f"Feature {i}: {feature.get('name', 'Unnamed Feature')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Description:**")
                        st.write(feature.get("description", "No description available"))
                        st.write(f"**Complexity:** {feature.get('complexity', 'Unknown')}")
                    with col2:
                        st.write(f"**Duration:** {feature.get('duration_days', 'N/A')} days")
                        st.write(f"**Hours:** {feature.get('hours', 'N/A')} hours")
        
        # Requirements (fallback for older data structure)
        if project.get("requirements"):
            st.subheader("Requirements")
            for i, req in enumerate(project["requirements"], 1):
                st.write(f"{i}. {req}")
        
        # Analysis summary (fallback for older data structure)
        if project.get("analysis_summary"):
            st.subheader("Analysis Summary")
            st.markdown(project["analysis_summary"])
        
        # Delete project option
        st.divider()
        with st.expander("⚠️ Danger Zone"):
            st.warning("This action cannot be undone!")
            if st.button("🗑️ Delete This Project", type="secondary"):
                result = api_client.delete_project(
                    st.session_state.selected_project,
                    st.session_state.user_token
                )
                if result["success"]:
                    st.success("Project deleted successfully!")
                    st.session_state.current_page = 'projects'
                    st.session_state.selected_project = None
                    st.rerun()
                else:
                    st.error("Failed to delete project")
    else:
        st.error("Failed to load project details")

def main():
    """Main application function"""
    init_session_state()
    
    # Show sidebar if authenticated
    if st.session_state.authenticated:
        show_sidebar()
    
    # Route to appropriate page
    if not st.session_state.authenticated:
        show_login_page()
    else:
        if st.session_state.current_page == 'dashboard':
            show_dashboard()
        elif st.session_state.current_page == 'upload':
            show_upload_page()
        elif st.session_state.current_page == 'projects':
            show_projects_page()
        elif st.session_state.current_page == 'project_detail':
            show_project_detail()
        else:
            show_dashboard()

if __name__ == "__main__":
    main()