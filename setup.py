from setuptools import setup
import json


with open("metadata.json", encoding="utf-8") as fp:
    metadata = json.load(fp)


setup(
    name="lexibank_dyenindoeuropean",
    description=metadata["title"],
    license=metadata.get("license", ""),
    url=metadata.get("url", ""),
    py_modules=["lexibank_dyenindoeuropean"],
    include_package_data=True,
    zip_safe=False,
    entry_points={"lexibank.dataset": ["dyenindoeuropean=lexibank_dyenindoeuropean:Dataset"]},
    install_requires=["pylexibank>=3.0"],
)
