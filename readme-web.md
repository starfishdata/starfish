
#### Step 2: Start the Backend

```bash
# Install Python dependencies
pip install -r api/requirements.txt

# Start the API server
python -m web.api.main
```

#### Step 3: Start the Frontend

```bash
NODE_OPTIONS='--inspect' 
npm run dev
```

#### Step 4: Debug the Frontend

```bash
NODE_OPTIONS='--inspect' npm run dev
```
