from parser import analyze_repository


repo = "../demo-repo"

result = analyze_repository(repo)

for file in result:
    print("\nFILE:", file["file"])

    print("Functions:")
    for function in file["functions"]:
        print(
            f"  {function['name']} "
            f"({function['line']}-{function['end_line']}) "
            f"calls={function['calls']}"
        )

        print("    CODE:")
        print(function["code"])

    print("Classes:", file["classes"])
    print("Imports:", file["imports"])
    print("LOC:", file["loc"])