"""Seamless CLI interface for one-click provider onboarding."""

import asyncio
import sys
import time
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich.table import Table

from .config_manager import ConfigManager
from .onboarding_orchestrator import OnboardingOrchestrator, OnboardingProgress, OnboardingStep
from .utils.logger import setup_logging, get_logger


class SeamlessCLI:
    """Seamless CLI for one-click provider onboarding."""
    
    def __init__(self):
        """Initialize seamless CLI."""
        self.console = Console()
        self.logger = get_logger(__name__)
        
        # Initialize configuration
        self.config = ConfigManager()
        
        # Initialize orchestrator
        self.orchestrator = OnboardingOrchestrator(self.config)
        self.orchestrator.set_progress_callback(self._on_progress_update)
        
        # Progress tracking
        self.current_progress: Optional[OnboardingProgress] = None
        self.progress_display = None
        self.live_display = None
    
    def run(self) -> None:
        """Run the seamless onboarding process."""
        try:
            # Setup logging
            setup_logging("INFO")
            
            # Show banner
            self._show_banner()
            
            # Get credentials
            username, password = self._get_credentials()
            
            # Authenticate
            if not self._authenticate(username, password):
                self.console.print("\n[red]❌ Authentication failed. Exiting.[/red]")
                sys.exit(1)
            
            # Show onboarding overview
            self._show_onboarding_overview(username)
            
            # Confirm start
            if not self._confirm_start():
                self.console.print("\n[yellow]Onboarding cancelled by user.[/yellow]")
                sys.exit(0)
            
            # Run onboarding
            asyncio.run(self._run_onboarding(username))
            
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Onboarding interrupted by user.[/yellow]")
            self._cleanup()
            sys.exit(1)
        except Exception as e:
            self.console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
            self.logger.error(f"Seamless CLI failed: {e}")
            self._cleanup()
            sys.exit(1)
    
    def _show_banner(self) -> None:
        """Show application banner."""
        banner_text = Text.assemble(
            ("🚀 ZanSoc", "bold blue"),
            (" Provider Onboarding", "white"),
        )
        
        banner = Panel(
            Align.center(banner_text),
            title="Welcome",
            border_style="blue",
            padding=(1, 2),
        )
        
        self.console.print(banner)
        self.console.print()
        
        # Show system info
        system_info = self.orchestrator.platform_utils.get_system_info()
        info_text = f"Platform: {system_info.platform.value} | Architecture: {system_info.architecture.value} | Python: {system_info.python_version}"
        self.console.print(f"[dim]{info_text}[/dim]")
        self.console.print()
    
    def _get_credentials(self) -> tuple[str, str]:
        """Get user credentials.
        
        Returns:
            Tuple of (username, password)
        """
        self.console.print("[bold]Please enter your credentials:[/bold]")
        
        username = self.console.input("Username: ").strip()
        if not username:
            username = "admin"  # Default for demo
        
        password = self.console.input("Password: ", password=True).strip()
        if not password:
            password = "admin"  # Default for demo
        
        return username, password
    
    def _authenticate(self, username: str, password: str) -> bool:
        """Authenticate user credentials.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            True if authentication successful
        """
        # Simple authentication (matches existing CLI)
        if username == "admin" and password == "admin":
            self.console.print("[green]✅ Authentication successful![/green]")
            return True
        else:
            return False
    
    def _show_onboarding_overview(self, username: str) -> None:
        """Show onboarding overview.
        
        Args:
            username: Username
        """
        overview = Panel(
            f"""[bold]Welcome {username}![/bold]

This tool will automatically set up your device as a ZanSoc compute provider.

[bold cyan]What will happen:[/bold cyan]
• 📝 Register your provider account
• 🔧 Install miniconda and Python environment  
• 📦 Clone ZanSoc repository and install dependencies
• 🌐 Install and configure Tailscale VPN
• ⚡ Connect to Ray distributed compute cluster
• ✅ Verify all connections and complete setup

[bold yellow]Requirements:[/bold yellow]
• Ubuntu/Linux system with internet connection
• Sudo privileges for system installations
• Approximately 5-10 minutes for complete setup

[bold green]After completion:[/bold green]
• Your device will be ready to earn rewards
• You'll be connected to the ZanSoc network
• Compute tasks will be automatically distributed to your node
""",
            title="🚀 Provider Onboarding Overview",
            border_style="cyan",
            padding=(1, 2),
        )
        
        self.console.print(overview)
    
    def _confirm_start(self) -> bool:
        """Confirm user wants to start onboarding.
        
        Returns:
            True if user confirms
        """
        response = self.console.input("\n[bold]Ready to start? (Y/n): [/bold]").strip().lower()
        return response in ('', 'y', 'yes')
    
    async def _run_onboarding(self, username: str) -> None:
        """Run the onboarding process with live progress display.
        
        Args:
            username: Username for registration
        """
        # Create progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console,
            transient=False
        )
        
        with progress:
            # Add main progress task
            main_task = progress.add_task("Starting onboarding...", total=6)
            
            # Create layout for live display
            layout = Layout()
            layout.split_column(
                Layout(name="progress", size=3),
                Layout(name="status", size=10),
                Layout(name="info", size=5)
            )
            
            # Start live display
            with Live(layout, console=self.console, refresh_per_second=2) as live:
                self.live_display = live
                self.progress_display = progress
                
                # Update layout
                layout["progress"].update(progress)
                layout["status"].update(Panel("Initializing...", title="Status"))
                layout["info"].update(Panel("Starting onboarding process...", title="Current Step"))
                
                # Run onboarding
                result = await self.orchestrator.start_onboarding(username)
                
                # Update final progress
                progress.update(main_task, completed=6)
                
                # Show result
                if result.success:
                    self._show_success(result)
                else:
                    self._show_failure(result)
    
    def _on_progress_update(self, progress: OnboardingProgress) -> None:
        """Handle progress updates from orchestrator.
        
        Args:
            progress: Current progress
        """
        self.current_progress = progress
        
        if self.progress_display and self.live_display:
            # Update progress display
            completed = len(progress.completed_steps)
            current_step_name = self._get_step_display_name(progress.current_step)
            
            # Update status panel
            status_content = self._create_status_panel(progress)
            info_content = f"[bold]{current_step_name}[/bold]\n\nCompleted: {completed}/{progress.total_steps}"
            
            # Update layout
            layout = self.live_display.renderable
            layout["status"].update(Panel(status_content, title="Progress"))
            layout["info"].update(Panel(info_content, title="Current Step"))
    
    def _create_status_panel(self, progress: OnboardingProgress) -> str:
        """Create status panel content.
        
        Args:
            progress: Current progress
            
        Returns:
            Status panel content
        """
        lines = []
        
        for i, step in enumerate([
            OnboardingStep.REGISTRATION,
            OnboardingStep.ENVIRONMENT_SETUP,
            OnboardingStep.TAILSCALE_SETUP,
            OnboardingStep.RAY_CONNECTION,
            OnboardingStep.VERIFICATION,
            OnboardingStep.COMPLETION
        ]):
            step_name = self._get_step_display_name(step)
            
            if step in progress.completed_steps:
                lines.append(f"[green]✅ {step_name}[/green]")
            elif step == progress.current_step:
                lines.append(f"[yellow]🔄 {step_name}[/yellow]")
            elif step in progress.failed_steps:
                lines.append(f"[red]❌ {step_name}[/red]")
            else:
                lines.append(f"[dim]⏳ {step_name}[/dim]")
        
        return "\n".join(lines)
    
    def _get_step_display_name(self, step: OnboardingStep) -> str:
        """Get display name for step.
        
        Args:
            step: Onboarding step
            
        Returns:
            Display name
        """
        names = {
            OnboardingStep.REGISTRATION: "Provider Registration",
            OnboardingStep.ENVIRONMENT_SETUP: "Environment Setup",
            OnboardingStep.TAILSCALE_SETUP: "Network Configuration",
            OnboardingStep.RAY_CONNECTION: "Cluster Connection",
            OnboardingStep.VERIFICATION: "System Verification",
            OnboardingStep.COMPLETION: "Finalization"
        }
        return names.get(step, step.value.replace('_', ' ').title())
    
    def _show_success(self, result) -> None:
        """Show success message.
        
        Args:
            result: Onboarding result
        """
        self.console.print()
        
        success_panel = Panel(
            f"""[bold green]🎉 Congratulations! Your device is now a ZanSoc provider![/bold green]

[bold]Provider Details:[/bold]
• Provider ID: {result.data.get('provider_id', 'Unknown')}
• Setup Time: {result.data.get('total_time', 0):.1f} seconds
• Completed Steps: {result.data.get('completed_steps', 0)}/6

[bold cyan]What's Next:[/bold cyan]
• Your device is now connected to the ZanSoc network
• Ray cluster tasks will be automatically distributed to your node
• You can monitor your earnings and status through the dashboard
• Keep your device online to maximize rewards

[bold yellow]Important:[/bold yellow]
• Your Tailscale VPN connection keeps you securely connected
• Ray cluster connection enables distributed computing
• Your provider status is now ACTIVE

[green]🚀 Welcome to the ZanSoc network![/green]
""",
            title="✅ Onboarding Complete",
            border_style="green",
            padding=(1, 2),
        )
        
        self.console.print(success_panel)
        
        # Show provider info table
        if self.current_progress and self.current_progress.provider_id:
            provider = self.orchestrator.provider_manager.get_provider(self.current_progress.provider_id)
            if provider:
                self._show_provider_info_table(provider)
    
    def _show_failure(self, result) -> None:
        """Show failure message.
        
        Args:
            result: Onboarding result
        """
        self.console.print()
        
        failure_panel = Panel(
            f"""[bold red]❌ Onboarding Failed[/bold red]

[bold]Error Details:[/bold]
• Failed Step: {self._get_step_display_name(result.step)}
• Error: {result.error or 'Unknown error'}
• Message: {result.message}

[bold yellow]Troubleshooting:[/bold yellow]
• Check your internet connection
• Ensure you have sudo privileges
• Verify system requirements are met
• Try running the installer again

[bold cyan]Get Help:[/bold cyan]
• Check the logs for detailed error information
• Contact support with your provider ID (if created)
• Visit our documentation for troubleshooting guides

[dim]You can run this installer again to retry the setup process.[/dim]
""",
            title="❌ Setup Failed",
            border_style="red",
            padding=(1, 2),
        )
        
        self.console.print(failure_panel)
    
    def _show_provider_info_table(self, provider) -> None:
        """Show provider information table.
        
        Args:
            provider: Provider instance
        """
        table = Table(title="Provider Information", show_header=True, header_style="bold cyan")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Provider ID", provider.id)
        table.add_row("Username", provider.username)
        table.add_row("Status", provider.status.value.title())
        table.add_row("Platform", provider.platform or "Detected")
        table.add_row("Tailscale IP", provider.tailscale_ip or "Connected")
        table.add_row("Ray Node ID", provider.ray_node_id or "Connected")
        table.add_row("Created", provider.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        
        self.console.print()
        self.console.print(table)
    
    def _cleanup(self) -> None:
        """Cleanup on failure or interruption."""
        try:
            if self.orchestrator:
                self.orchestrator.cleanup_on_failure()
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")


def main():
    """Main entry point for seamless CLI."""
    cli = SeamlessCLI()
    cli.run()


if __name__ == "__main__":
    main()