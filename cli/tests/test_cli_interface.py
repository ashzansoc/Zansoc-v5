"""Tests for CLIInterface class."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from rich.console import Console

from zansoc_cli.cli_interface import CLIInterface
from zansoc_cli.config_manager import ConfigManager
from zansoc_cli.database import DatabaseManager
from zansoc_cli.provider_manager import ProviderManager
from zansoc_cli.models import Provider, ProviderStatus


class TestCLIInterface:
    """Test cases for CLIInterface."""
    
    def setup_method(self):
        """Setup test fixtures."""
        # Create temporary database file
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Mock config to use temp database
        self.config = ConfigManager()
        with patch.object(self.config, 'get_database_path', return_value=self.temp_db.name):
            self.cli = CLIInterface(self.config)
    
    def teardown_method(self):
        """Cleanup test fixtures."""
        # Remove temporary database file
        if os.path.exists(self.temp_db.name):
            os.unlink(self.temp_db.name)
    
    def test_initialization(self):
        """Test CLI interface initialization."""
        assert self.cli.config == self.config
        assert isinstance(self.cli.console, Console)
    
    @patch('click.prompt')
    def test_authentication_success(self, mock_prompt):
        """Test successful authentication."""
        mock_prompt.side_effect = ["admin", "admin"]
        
        result = self.cli.authenticate()
        assert result is True
    
    @patch('click.prompt')
    def test_authentication_failure(self, mock_prompt):
        """Test failed authentication."""
        mock_prompt.side_effect = ["wrong", "wrong"] * 3
        
        result = self.cli.authenticate()
        assert result is False
    
    @patch('click.prompt')
    def test_role_selection_provider(self, mock_prompt):
        """Test provider role selection."""
        mock_prompt.return_value = 1
        
        role = self.cli.select_role()
        assert role == "provider"
    
    @patch('click.prompt')
    def test_role_selection_user(self, mock_prompt):
        """Test user role selection."""
        mock_prompt.return_value = 2
        
        role = self.cli.select_role()
        assert role == "user"
    
    @patch('click.prompt')
    def test_role_selection_both(self, mock_prompt):
        """Test both roles selection."""
        mock_prompt.return_value = 3
        
        role = self.cli.select_role()
        assert role == "both"
    
    @patch('zansoc_cli.cli_interface.CLIInterface.prompt_choice')
    def test_role_selection_provider(self, mock_prompt_choice):
        """Test provider role selection."""
        mock_prompt_choice.return_value = "Provider - Contribute compute resources"
        
        role = self.cli.select_role()
        assert role == "provider"
    
    @patch('zansoc_cli.cli_interface.CLIInterface.prompt_choice')
    def test_role_selection_user(self, mock_prompt_choice):
        """Test user role selection."""
        mock_prompt_choice.return_value = "User - Use compute resources"
        
        role = self.cli.select_role()
        assert role == "user"
    
    @patch('zansoc_cli.cli_interface.CLIInterface.prompt_choice')
    def test_role_selection_both(self, mock_prompt_choice):
        """Test both roles selection."""
        mock_prompt_choice.return_value = "Both - Provider and User"
        
        role = self.cli.select_role()
        assert role == "both"
    
    def test_show_progress(self):
        """Test progress display."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_progress("Test Step", "starting")
        self.cli.show_progress("Test Step", "running")
        self.cli.show_progress("Test Step", "success")
        self.cli.show_progress("Test Step", "error")
    
    def test_show_congratulations(self):
        """Test congratulations screen display."""
        provider_info = {
            "id": "test-provider-123",
            "tailscale_ip": "100.64.0.1",
            "ray_status": "connected",
            "platform": "linux-x86_64"
        }
        
        # This test mainly ensures no exceptions are raised
        self.cli.show_congratulations(provider_info)
    
    @patch('click.confirm')
    def test_handle_error_retry(self, mock_confirm):
        """Test error handling with retry."""
        mock_confirm.return_value = True
        
        error = Exception("Test error")
        result = self.cli.handle_error(error, "test_step")
        
        assert result is True
    
    @patch('click.confirm')
    def test_handle_error_no_retry(self, mock_confirm):
        """Test error handling without retry."""
        mock_confirm.return_value = False
        
        error = Exception("Test error")
        result = self.cli.handle_error(error, "test_step")
        
        assert result is False
    
    def test_show_success(self):
        """Test success message display."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_success("Test success message")
    
    def test_show_error(self):
        """Test error message display."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_error("Test error message")
    
    def test_show_warning(self):
        """Test warning message display."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_warning("Test warning message")
    
    def test_show_info_panel(self):
        """Test info panel display."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_info_panel("Test Title", "Test content", "blue")
    
    def test_show_table(self):
        """Test table display."""
        headers = ["Column 1", "Column 2"]
        rows = [["Row 1 Col 1", "Row 1 Col 2"], ["Row 2 Col 1", "Row 2 Col 2"]]
        
        # This test mainly ensures no exceptions are raised
        self.cli.show_table("Test Table", headers, rows)
    
    @patch('click.confirm')
    def test_confirm_action(self, mock_confirm):
        """Test confirmation prompt."""
        mock_confirm.return_value = True
        
        result = self.cli.confirm_action("Test confirmation?")
        assert result is True
        
        mock_confirm.assert_called_once_with("Test confirmation?", default=True)
    
    @patch('click.prompt')
    def test_prompt_choice(self, mock_prompt):
        """Test choice prompt."""
        mock_prompt.return_value = 2
        
        choices = ["Option 1", "Option 2", "Option 3"]
        result = self.cli.prompt_choice("Select an option:", choices)
        
        assert result == "Option 2"
    
    @patch('click.prompt')
    def test_prompt_choice_invalid_then_valid(self, mock_prompt):
        """Test choice prompt with invalid then valid input."""
        mock_prompt.side_effect = [5, 1]  # Invalid then valid
        
        choices = ["Option 1", "Option 2", "Option 3"]
        result = self.cli.prompt_choice("Select an option:", choices)
        
        assert result == "Option 1"
    
    def test_show_provider_list_empty(self):
        """Test showing empty provider list."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_provider_list([])
    
    def test_show_provider_list_with_providers(self):
        """Test showing provider list with data."""
        from datetime import datetime
        
        providers = [
            Provider(
                id="test-provider-1",
                username="user1",
                status=ProviderStatus.ACTIVE,
                created_at=datetime.now(),
                platform="linux-x86_64"
            ),
            Provider(
                id="test-provider-2", 
                username="user2",
                status=ProviderStatus.REGISTERING,
                created_at=datetime.now()
            )
        ]
        
        # This test mainly ensures no exceptions are raised
        self.cli.show_provider_list(providers)
    
    @patch('time.sleep')
    def test_show_animated_loading(self, mock_sleep):
        """Test animated loading display."""
        # This test mainly ensures no exceptions are raised
        self.cli.show_animated_loading("Loading test...", 0.1)
        mock_sleep.assert_called_once_with(0.1)
    
    def test_show_progress_bar(self):
        """Test progress bar creation."""
        progress = self.cli.show_progress_bar(5, "Test Progress")
        assert progress is not None
    
    @patch('zansoc_cli.cli_interface.CLIInterface._start_provider_onboarding')
    @patch('zansoc_cli.cli_interface.CLIInterface.prompt_choice')
    def test_main_menu_provider_onboarding(self, mock_prompt_choice, mock_onboarding):
        """Test main menu provider onboarding selection."""
        mock_prompt_choice.side_effect = [
            "Join as Provider - Contribute compute resources",
            "Exit"
        ]
        
        self.cli._show_main_menu()
        
        mock_onboarding.assert_called_once()
    
    @patch('zansoc_cli.cli_interface.CLIInterface.prompt_choice')
    def test_main_menu_exit(self, mock_prompt_choice):
        """Test main menu exit selection."""
        mock_prompt_choice.return_value = "Exit"
        
        # This test mainly ensures no exceptions are raised
        self.cli._show_main_menu()