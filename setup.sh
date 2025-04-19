echo "--------------------------------------"
echo "Setting up environment for LLM-REST"
echo "Trying to create the Python Environment llm-rest using Python 3.11..."

if conda env list | grep -qE "^llm-rest\s"; then
  echo "Environment llm-rest already exists. Skipping..."
else
  echo "Creating conda environment llm-rest..."
  conda create -y -n llm-rest python=3.11
  echo "Environment llm-rest created successfully."
fi

echo "Installing packages from into environment llm-rest..."
conda run -n llm-rest pip install --upgrade pip
conda run -n llm-rest pip install -r ./requirements.txt

spacy_whl="lib/en_core_web_sm-3.8.0-py3-none-any.whl"

if [ -f "$spacy_whl" ]; then
  echo "Installing local spacy model en_core_web_sm..."
  conda run -n llm-rest pip install "$spacy_whl"
  echo "Spacy model installed successfully."
else
  echo "Try to download the spacy model from the internet..."
  conda run -n llm-rest python -m spacy download en_core_web_sm
fi

echo "Packages installed successfully."
