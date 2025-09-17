"""CLI interface for user interaction and display."""

import click
import time
from typing import Dict, Any, Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

from .config_manager import ConfigManager
from .database import DatabaseManager
from .provider_manager import ProviderManager
from .models import Provider, ProviderStatus
from .utils.logger import get_logger


class CLIInterface:
    """Handles command-line user interface and interactions."""
    
    def __init__(self, config_manager: ConfigManager):
        """Initialize CLI interface.
        
        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.console = Console()
        self.logger = get_logger(__name__)
        
        # Initialize database and provider manager
        db_path = self.config.get_database_path()
        self.db = DatabaseManager(str(db_path))
        self.provider_manager = ProviderManager(self.db)
    
    def start(self) -> None:
        """Start the CLI application."""
        self.show_banner()
        
        if self.authenticate():
            self.show_welcome()
            self._show_main_menu()
        else:
            self.console.print("\n[red]Authentication failed. Exiting.[/red]")
    
    def _show_main_menu(self) -> None:
        """Show the main menu and handle user selection."""
        while True:
            try:
                choices = [
                    "Join as Provider - Contribute compute resources",
                    "Join as User - Use compute resources (Coming Soon)",
                    "View Provider Status",
                    "List All Providers",
                    "Exit"
                ]
                
                selected = self.prompt_choice(
                    "What would you like to do?",
                    choices
                )
                
                if "Join as Provider" in selected:
                    self.console.print("\n[green]Starting provider onboarding process...[/green]")
                    self._start_provider_onboarding()
                    
                elif "Join as User" in selected:
                    self.show_info_panel(
                        "Coming Soon",
                        "User features are being developed in upcoming tasks.\nFor now, you can join as a provider to contribute compute resources.",
                        "yellow"
                    )
                    
                elif "View Provider Status" in selected:
                    self._show_provider_status_menu()
                    
                elif "List All Providers" in selected:
                    self._list_all_providers()
                    
                elif "Exit" in selected:
                    self.console.print("\n[cyan]Thank you for using ZanSoc! 👋[/cyan]")
                    break
                    
            except KeyboardInterrupt:
                self.console.print("\n\n[cyan]Goodbye! 👋[/cyan]")
                break
            except Exception as e:
                self.logger.error(f"Main menu error: {e}")
                self.show_error(f"An error occurred: {e}")
                try:
                    if not self.confirm_action("Would you like to continue?"):
                        break
                except:
                    break
    
    def _show_provider_status_menu(self) -> None:
        """Show provider status menu."""
        username = self.config.get("auth.username", "admin")
        provider = self.provider_manager.get_provider_by_username(username)
        
        if provider:
            self._show_provider_status(provider.id)
        else:
            self.show_warning(f"No provider found for username '{username}'")
            if self.confirm_action("Would you like to register as a provider?"):
                self._start_provider_onboarding()
    
    def _list_all_providers(self) -> None:
        """List all providers in the system."""
        try:
            providers = self.provider_manager.list_providers()
            self.show_provider_list(providers)
            
            if providers:
                self.console.print(f"\n[cyan]Total providers: {len(providers)}[/cyan]")
                
                # Show status breakdown
                status_counts = {}
                for provider in providers:
                    status = provider.status.value
                    status_counts[status] = status_counts.get(status, 0) + 1
                
                self.console.print("\n[cyan]Status breakdown:[/cyan]")
                for status, count in status_counts.items():
                    self.console.print(f"• {status}: {count}")
            
        except Exception as e:
            self.logger.error(f"Failed to list providers: {e}")
            self.show_error(f"Failed to list providers: {e}")
    
    def show_banner(self) -> None:
        """Display application banner."""
        banner = Text.assemble(
            ("ZanSoc", "bold blue"),
            (" Distributed Compute Network", "white"),
        )
        
        panel = Panel(
            banner,
            title="Welcome",
            border_style="blue",
            padding=(1, 2),
        )
        
        self.console.print(panel)
        self.console.print()
    
    def authenticate(self) -> bool:
        """Handle user authentication.
        
        Returns:
            True if authentication successful
        """
        max_attempts = self.config.get("auth.max_attempts", 3)
        expected_username = self.config.get("auth.username", "admin")
        expected_password = self.config.get("auth.password", "admin")
        
        for attempt in range(max_attempts):
            self.console.print(f"[cyan]Authentication Required[/cyan] (Attempt {attempt + 1}/{max_attempts})")
            
            username = click.prompt("Username", type=str)
            password = click.prompt("Password", type=str, hide_input=True)
            
            if username == expected_username and password == expected_password:
                self.logger.info(f"User {username} authenticated successfully")
                return True
            else:
                self.console.print("[red]Invalid credentials. Please try again.[/red]\n")
                self.logger.warning(f"Failed authentication attempt for user: {username}")
        
        self.logger.error(f"Authentication failed after {max_attempts} attempts")
        return False
    
    def show_welcome(self) -> None:
        """Display welcome message."""
        welcome_text = Text.assemble(
            ("Welcome to ZanSoc Dashboard!", "bold green"),
        )
        
        panel = Panel(
            welcome_text,
            title="Success",
            border_style="green",
            padding=(1, 2),
        )
        
        self.console.print(panel)
        self.console.print()
    
    def select_role(self) -> str:
        """Handle role selection.
        
        Returns:
            Selected role ('provider', 'user', or 'both')
        """
        choices = [
            "Provider - Contribute compute resources",
            "User - Use compute resources", 
            "Both - Provider and User"
        ]
        
        selected = self.prompt_choice(
            "Please select your role in the ZanSoc network:",
            choices,
            default=choices[0]
        )
        
        # Map selection to role
        if "Provider" in selected and "Both" not in selected:
            self.logger.info("User selected Provider role")
            return "provider"
        elif "User" in selected and "Both" not in selected:
            self.logger.info("User selected User role")
            return "user"
        else:
            self.logger.info("User selected Both roles")
            return "both"
    
    def show_progress(self, step: str, status: str) -> None:
        """Display progress for a step.
        
        Args:
            step: Step name
            status: Status ('starting', 'running', 'success', 'error')
        """
        if status == "starting":
            self.console.print(f"[yellow]Starting:[/yellow] {step}")
        elif status == "running":
            self.console.print(f"[blue]Running:[/blue] {step}")
        elif status == "success":
            self.console.print(f"[green]✓ Completed:[/green] {step}")
        elif status == "error":
            self.console.print(f"[red]✗ Failed:[/red] {step}")
    
    def show_congratulations(self, provider_info: Dict[str, Any]) -> None:
        """Display congratulations screen.
        
        Args:
            provider_info: Provider information dictionary
        """
        congrats_text = Text.assemble(
            ("🎉 Congratulations! 🎉", "bold green"),
            ("\n\nYour device has been successfully enrolled as a ZanSoc provider!", "white"),
        )
        
        info_text = Text()
        info_text.append(f"Provider ID: {provider_info.get('id', 'N/A')}\n", style="cyan")
        info_text.append(f"Tailscale IP: {provider_info.get('tailscale_ip', 'N/A')}\n", style="cyan")
        info_text.append(f"Ray Node Status: {provider_info.get('ray_status', 'N/A')}\n", style="cyan")
        info_text.append(f"Platform: {provider_info.get('platform', 'N/A')}\n", style="cyan")
        
        panel = Panel(
            Text.assemble(congrats_text, "\n\n", info_text),
            title="Success",
            border_style="green",
            padding=(1, 2),
        )
        
        self.console.print(panel)
        
        # Next steps
        self.console.print("\n[cyan]Next Steps:[/cyan]")
        self.console.print("• Your device is now part of the ZanSoc network")
        self.console.print("• You'll start earning rewards for providing compute resources")
        self.console.print("• Monitor your node status through the Ray dashboard")
        self.console.print("• Keep your device online to maximize earnings")
    
    def handle_error(self, error: Exception, step: str) -> bool:
        """Handle and display error information.
        
        Args:
            error: Exception that occurred
            step: Step where error occurred
            
        Returns:
            True if user wants to retry
        """
        self.console.print(f"\n[red]Error in step '{step}':[/red]")
        self.console.print(f"[red]{str(error)}[/red]")
        
        retry = click.confirm("\nWould you like to retry this step?", default=True)
        return retry
    
    def show_spinner(self, message: str):
        """Show a spinner with message.
        
        Args:
            message: Message to display with spinner
            
        Returns:
            Progress context manager
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=True,
        )
    
    def show_progress_bar(self, total_steps: int, description: str = "Processing"):
        """Show a progress bar for multi-step operations.
        
        Args:
            total_steps: Total number of steps
            description: Description of the operation
            
        Returns:
            Progress context manager
        """
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
        )
    
    def show_table(self, title: str, headers: List[str], rows: List[List[str]]) -> None:
        """Display a formatted table.
        
        Args:
            title: Table title
            headers: Column headers
            rows: Table rows
        """
        table = Table(title=title, show_header=True, header_style="bold magenta")
        
        for header in headers:
            table.add_column(header)
        
        for row in rows:
            table.add_row(*row)
        
        self.console.print(table)
    
    def confirm_action(self, message: str, default: bool = True) -> bool:
        """Ask user for confirmation.
        
        Args:
            message: Confirmation message
            default: Default choice
            
        Returns:
            True if user confirms
        """
        return click.confirm(message, default=default)
    
    def prompt_choice(self, message: str, choices: List[str], default: Optional[str] = None) -> str:
        """Prompt user to select from choices.
        
        Args:
            message: Prompt message
            choices: List of available choices
            default: Default choice
            
        Returns:
            Selected choice
        """
        while True:
            self.console.print(f"\n[cyan]{message}[/cyan]")
            for i, choice in enumerate(choices, 1):
                marker = " (default)" if choice == default else ""
                self.console.print(f"{i}. {choice}{marker}")
            
            try:
                selection = click.prompt("\nEnter your choice", type=int)
                if 1 <= selection <= len(choices):
                    return choices[selection - 1]
                else:
                    self.console.print(f"[red]Please enter a number between 1 and {len(choices)}[/red]")
            except (ValueError, click.Abort):
                if default:
                    return default
                self.console.print("[red]Invalid input. Please enter a number.[/red]")
    
    def show_info_panel(self, title: str, content: str, style: str = "blue") -> None:
        """Display an information panel.
        
        Args:
            title: Panel title
            content: Panel content
            style: Panel border style
        """
        panel = Panel(
            content,
            title=title,
            border_style=style,
            padding=(1, 2),
        )
        self.console.print(panel)
    
    def show_warning(self, message: str) -> None:
        """Display a warning message.
        
        Args:
            message: Warning message
        """
        self.console.print(f"[yellow]⚠️  Warning: {message}[/yellow]")
    
    def show_error(self, message: str) -> None:
        """Display an error message.
        
        Args:
            message: Error message
        """
        self.console.print(f"[red]❌ Error: {message}[/red]")
    
    def show_success(self, message: str) -> None:
        """Display a success message.
        
        Args:
            message: Success message
        """
        self.console.print(f"[green]✅ {message}[/green]")
    
    def clear_screen(self) -> None:
        """Clear the console screen."""
        self.console.clear()
    
    def pause(self, message: str = "Press any key to continue...") -> None:
        """Pause execution and wait for user input.
        
        Args:
            message: Message to display
        """
        click.pause(message)
    
    def show_provider_list(self, providers: List[Provider]) -> None:
        """Display a formatted list of providers.
        
        Args:
            providers: List of Provider instances
        """
        if not providers:
            self.console.print("[yellow]No providers found.[/yellow]")
            return
        
        headers = ["ID", "Username", "Status", "Platform", "Created", "Last Seen"]
        rows = []
        
        for provider in providers:
            rows.append([
                provider.id[:12] + "..." if len(provider.id) > 15 else provider.id,
                provider.username,
                provider.status.value,
                provider.platform or "N/A",
                provider.created_at.strftime("%Y-%m-%d %H:%M"),
                provider.last_seen.strftime("%Y-%m-%d %H:%M") if provider.last_seen else "Never",
            ])
        
        self.show_table("ZanSoc Providers", headers, rows)
    
    def show_animated_loading(self, message: str, duration: float = 2.0) -> None:
        """Show an animated loading sequence.
        
        Args:
            message: Loading message
            duration: Duration in seconds
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
            transient=False,
        ) as progress:
            task = progress.add_task(message, total=None)
            time.sleep(duration)
            progress.update(task, completed=True)
    
    def _start_provider_onboarding(self) -> None:
        """Start the provider onboarding process."""
        try:
            # Get current username (from authentication)
            username = self.config.get("auth.username", "admin")
            
            # Show onboarding overview
            self.show_info_panel(
                "Provider Onboarding",
                f"Welcome {username}! We'll help you join the ZanSoc network as a compute provider.\n\n"
                "This process will:\n"
                "• Register your provider account\n"
                "• Set up your development environment\n"
                "• Connect you to the distributed network\n"
                "• Configure your node for compute tasks",
                "blue"
            )
            
            if not self.confirm_action("Ready to start the onboarding process?"):
                return
            
            # Multi-step progress tracking
            steps = [
                "Registering provider account",
                "Creating onboarding session", 
                "Initializing provider status",
                "Preparing for next steps"
            ]
            
            with self.show_progress_bar(len(steps), "Provider Onboarding") as progress:
                task = progress.add_task("Starting onboarding...", total=len(steps))
                
                # Step 1: Register provider
                progress.update(task, description=steps[0])
                provider = self.provider_manager.register_provider(username)
                progress.advance(task)
                
                if not provider:
                    self.show_error("Failed to register provider")
                    return
                
                self.show_success(f"Provider registered with ID: {provider.id}")
                
                # Step 2: Create onboarding session
                progress.update(task, description=steps[1])
                session = self.provider_manager.create_onboarding_session(
                    provider.id, 
                    "registration"
                )
                progress.advance(task)
                
                if not session:
                    self.show_error("Failed to create onboarding session")
                    return
                
                self.show_success(f"Onboarding session created: {session.session_id[:20]}...")
                
                # Step 3: Update provider status
                progress.update(task, description=steps[2])
                self.provider_manager.update_session_step(
                    session.session_id,
                    "environment_setup",
                    completed_step="registration"
                )
                progress.advance(task)
                
                # Step 4: Finalize
                progress.update(task, description=steps[3])
                time.sleep(0.5)  # Brief pause for effect
                progress.advance(task)
            
            # Show completion message
            self.show_success("Provider onboarding initialization complete!")
            
            # Show next steps
            self.show_info_panel(
                "Next Steps",
                "The following steps will be implemented in upcoming tasks:\n\n"
                "🔧 Environment Setup\n"
                "   • Install miniconda with Python 3.13.7\n"
                "   • Clone ZanSoc repository\n"
                "   • Install dependencies\n\n"
                "🌐 Network Integration\n"
                "   • Install and configure Tailscale VPN\n"
                "   • Connect to ZanSoc private network\n\n"
                "⚡ Cluster Connection\n"
                "   • Connect to Ray cluster\n"
                "   • Register as compute node\n"
                "   • Verify connectivity",
                "yellow"
            )
            
            # Show current provider status
            self._show_provider_status(provider.id)
            
            # Ask if user wants to continue with manual setup
            if self.confirm_action("Would you like to see your provider status?", default=False):
                self.pause("Press Enter to continue...")
                
        except Exception as e:
            self.logger.error(f"Provider onboarding failed: {e}")
            self.show_error(f"Provider onboarding failed: {e}")
            
            try:
                if self.confirm_action("Would you like to try again?"):
                    self._start_provider_onboarding()
            except:
                pass  # User cancelled or input error
    
    def _show_provider_status(self, provider_id: str) -> None:
        """Show provider status information.
        
        Args:
            provider_id: Provider ID
        """
        try:
            status_info = self.provider_manager.get_provider_status(provider_id)
            if not status_info:
                self.show_warning(f"Provider {provider_id} not found")
                return
            
            provider = status_info['provider']
            session = status_info['session']
            summary = status_info['status_summary']
            
            # Create status table
            status_data = [
                ["Provider ID", provider.id],
                ["Username", provider.username],
                ["Status", provider.status.value.title()],
                ["Platform", provider.platform or "Not detected"],
                ["Tailscale IP", provider.tailscale_ip or "Not connected"],
                ["Ray Node ID", provider.ray_node_id or "Not connected"],
                ["Created", provider.created_at.strftime('%Y-%m-%d %H:%M:%S')],
                ["Last Seen", provider.last_seen.strftime('%Y-%m-%d %H:%M:%S') if provider.last_seen else "Never"],
            ]
            
            self.show_table("Provider Information", ["Field", "Value"], status_data)
            
            # Show session information if available
            if session:
                session_data = [
                    ["Session ID", session.session_id[:30] + "..."],
                    ["Current Step", session.current_step],
                    ["Completed Steps", str(len(session.completed_steps))],
                    ["Failed Steps", str(len(session.failed_steps))],
                    ["Created", session.created_at.strftime('%Y-%m-%d %H:%M:%S')],
                    ["Updated", session.updated_at.strftime('%Y-%m-%d %H:%M:%S')],
                ]
                
                self.show_table("Onboarding Session", ["Field", "Value"], session_data)
                
                # Show step details if available
                if session.completed_steps:
                    self.console.print("\n[green]✅ Completed Steps:[/green]")
                    for step in session.completed_steps:
                        self.console.print(f"  • {step}")
                
                if session.failed_steps:
                    self.console.print("\n[red]❌ Failed Steps:[/red]")
                    for step in session.failed_steps:
                        self.console.print(f"  • {step}")
            
            # Show status-specific information
            if provider.status == ProviderStatus.REGISTERING:
                self.show_info_panel(
                    "Next Steps",
                    "Your provider is registered but not yet active.\n"
                    "Complete the onboarding process to start contributing compute resources.",
                    "yellow"
                )
            elif provider.status == ProviderStatus.ACTIVE:
                self.show_info_panel(
                    "Status: Active",
                    "🎉 Your provider is active and contributing to the ZanSoc network!\n"
                    "Keep your device online to maximize earnings.",
                    "green"
                )
            elif provider.status == ProviderStatus.ERROR:
                self.show_info_panel(
                    "Status: Error",
                    "⚠️ Your provider encountered an error.\n"
                    "Check the logs or restart the onboarding process.",
                    "red"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to show provider status: {e}")
            self.show_error(f"Failed to show provider status: {e}")