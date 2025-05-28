# Starfish Data Generation Templates 🌟

Welcome to Starfish's collection of prebuilt data generation templates! This directory contains ready-to-use templates that you can load and run immediately to generate high-quality synthetic datasets.

## What are Data Generation Templates?

Data generation templates are **prebuilt** that encapsulate sophisticated data generation workflows. Instead of building everything from scratch, you can simply load a template and generate the exact type of data you need with just a few lines of code.

## How It Works

1. **Browse Available Templates**: Each template focuses on a specific data generation use case
2. **Load the Template**: Simple one-line import to get started
3. **Configure Parameters**: Customize the generation settings for your needs
4. **Generate Data**: Run the template to produce high-quality synthetic data
5. **Export & Use**: Data comes ready for training, testing, or evaluation

## Use the data-template CLI like this:
```
# List all templates
data-template list-templates

# List with details
data-template list-templates --detail

# Get template details
data-template get-template my_template

# Print schema
data-template print-schema my_template

# Print example
data-template print-example my_template

# Run template with interactive input
data-template run-template my_template

# Run template with input file
data-template run-template my_template --input-file input.json

# Run template and save output
data-template run-template my_template --input-file input.json --output-file output.json
```
## Source Code Location

The actual implementation of these templates can be found in:
```
src/starfish/data_gen_template/templates/
```



## Community & Contributions 🤝

Like what you see? We'd love your help in expanding our template collection! Here's how you can get involved:

- **Build Your Own Template**: Have an idea for a new template? We'd love to see it!
- **Request Templates**: Need a specific type of data generation? Let us know!
- **Community Contributions**: All templates in the `community/` folder come from amazing contributors like you
- **Get Help**: Questions about building templates? We're here to help!

Reach out to us if you want to contribute or have any requests - we're always happy to chat and help! ⭐