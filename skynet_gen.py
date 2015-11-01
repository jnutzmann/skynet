import argparse

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--file", nargs="*", action="append")
    p.add_argument("--dir", nargs="*", action="append")
    args = p.parse_args()
    print(args.file)
    print(args.dir)