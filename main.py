#!/usr/bin/env python3
"""
Main entry point per il sistema Multi-Agent Hub & Spoke
Ora con interfaccia Dash per UX professionale
"""

from app_dash import app
from utils.logging_config import get_logger


logger = get_logger("main")


def main():
    """Lancia l'app Dash"""
    logger.info("Avvio server Dash su http://127.0.0.1:8050")
    print("\n" + "="*60)
    print("MULTI-AGENT DATA ANALYSIS PLATFORM")
    print("="*60)
    print("\nAccedi all'applicazione su: http://localhost:8050")
    print("\nL'app si sta avviando...")
    
    # Avvia il server Dash
    app.run(debug=False, port=8050, host='127.0.0.1')


if __name__ == "__main__":
    main()

