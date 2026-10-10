"""Operações administrativas locais, indisponíveis na API pública."""
import argparse
from backend.server import load_store


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="operation", required=True)
    reset = sub.add_parser("reset")
    reset.add_argument("challenge")
    backup = sub.add_parser("backup")
    backup.add_argument("destination")
    args = parser.parse_args()
    store = load_store()
    if args.operation == "reset":
        store.reset(args.challenge)
        print("Progresso deste desafio reiniciado; tentativas e auditoria preservadas.")
    elif args.operation == "backup":
        store.backup(args.destination)
        print("Backup SQLite concluído.")


if __name__ == "__main__":
    main()
