"""Main entry point for ZanSoc CLI application."""

import sys
import click
from typing import Optional

from .cli_interface import CLIInterface
from .config_manager import ConfigManager
from .utils.logger import setup_logging


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Path to configuration file",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose logging",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug mode",
)
@click.version_option()
def main(config: Optional[str] = None, verbose: bool = False, debug: bool = False) -> None:
    """ZanSoc Provider Onboarding CLI
    
    Welcome to the ZanSoc distributed compute network!
    This tool will help you join as a resource provider.
    """
    try:
        # Setup logging
        log_level = "DEBUG" if debug else ("INFO" if verbose else "WARNING")
        setup_logging(log_level)
        
        # Initialize configuration
        config_manager = ConfigManager(config_path=config)
        
        # Initialize CLI interface
        cli = CLIInterface(config_manager)
        
        # Start the onboarding process
        cli.start()
        
    except KeyboardInterrupt:
        click.echo("\n\nOperation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        click.echo(f"\nUnexpected error: {e}", err=True)
        if debug:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()