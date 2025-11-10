import pkg_resources
from pathlib import Path

def get_installed_packages():
    """Return a dict of installed packages with their versions."""
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    return installed_packages

def update_requirements(requirements_file="requirements.txt", output_file=None):
    """Read packages from requirements.txt and update with installed versions."""
    req_path = Path(requirements_file)
    if not req_path.exists():
        print(f"❌ {requirements_file} not found.")
        return

    installed = get_installed_packages()
    updated_lines = []

    with req_path.open("r") as f:
        for line in f:
            pkg = line.strip()
            if not pkg or pkg.startswith("#"):
                updated_lines.append(line)
                continue

            pkg_name = pkg.split("==")[0].lower()
            version = installed.get(pkg_name)
            if version:
                updated_lines.append(f"{pkg_name}=={version}\n")
            else:
                print(f"⚠️  Package '{pkg_name}' not found in environment.")
                updated_lines.append(pkg + "\n")

    # Write to output file (default: overwrite same file)
    output_path = Path(output_file) if output_file else req_path
    with output_path.open("w") as f:
        f.writelines(updated_lines)

    print(f"✅ Updated package versions written to: {output_path}")

if __name__ == "__main__":
    # Example usage
    update_requirements("requirements.txt")
