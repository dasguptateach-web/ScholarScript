import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import ScholarScriptApp


def main():
    app = ScholarScriptApp()
    app.run()


if __name__ == "__main__":
    main()
