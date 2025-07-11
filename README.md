# BN Monitoring Project

This project builds Bayesian Networks (BNs) for APT attack flows and provides live monitoring and visualization via Prometheus and Grafana.

## Quickstart

### 1. Install Dependencies

Create and activate your virtual environment, then install requirements:

```
conda activate midterm_env
pip install -r requirements.txt
```

Ensure:

* Prometheus is installed and on your PATH
* Grafana is installed via Homebrew:

```
brew install grafana
```

## Start All Services

Run the entire stack:

```
make start
```

This will:

* Download APT attack flows into `inputs/`
* Generate BN `.xdsl` files into `xdsl_files/`
* Start Prometheus
* Start the BN Flask web service
* Start Grafana via Homebrew
* Upload dashboards to Grafana

## Manual Workflow

If you prefer manual steps, use these:

### Download APT JSON Files

```
make get
```

Stores APT JSONs in:

```
inputs/
```

### Generate BN Files

From downloaded JSONs:

```
make generate
```

Generates `.xdsl` files in:

```
xdsl_files/
```

### Run Prometheus

```
make run-prometheus
```

Prometheus UI:

[http://localhost:9090](http://localhost:9090)

### Run BN Flask Webservice

Starts the BN inference server:

```
make run-flask
```

Service runs at:

[http://localhost:8000](http://localhost:8000)

### Run Grafana

Start via Homebrew:

```
make run-grafana
```

Grafana UI:

[http://localhost:3000](http://localhost:3000)

(Default login: admin / admin)

### Generate Dashboards

Creates and uploads dashboards to Grafana:

```
make dashboards
```

## API Usage

### List All Nodes

See all evidence nodes for every APT:

```
curl http://localhost:8000/nodes | jq
```

Example:

```
{
  "BlackBastaRansomware": [
    "Phishing_Spearphishing_Attachm_attack_action_a3679838",
    "User_Execution_Malicious_File_attack_action_e5715d9b",
    ...
  ],
  "CobaltKittyCampaign": [
    "Spearphishing_Attachment_attack_action_508bc600",
    ...
  ]
}
```

### Get Current Beliefs

Retrieve all node probabilities:

```
curl http://localhost:8000/inference | jq
```

Example partial output:

```
{
  "BlackBastaRansomware": {
    "BlackBastaRansomwareOccurred": [0.5, 0.5],
    "Phishing_Spearphishing_Attachm_attack_action_a3679838": [0.5, 0.5],
    ...
  }
}
```

Each value is:

```
[ P(False), P(True) ]
```

### Submit Evidence

Update beliefs in the BN:

```
curl -X POST http://localhost:8000/evidence \
  -H "Content-Type: application/json" \
  -d '{"evidence": [
    "Phishing_Spearphishing_Attachm_attack_action_a3679838",
    "User_Execution_Malicious_File_attack_action_e5715d9b"
  ]}'
```

## Example Workflow

```
# 1. Check beliefs
curl http://localhost:8000/inference | jq '.BlackBastaRansomware'

# 2. Submit evidence
curl -X POST http://localhost:8000/evidence \
  -H "Content-Type: application/json" \
  -d '{"evidence": ["Phishing_Spearphishing_Attachm_attack_action_a3679838"]}'

# 3. Re-check beliefs
curl http://localhost:8000/inference | jq '.BlackBastaRansomware'
```

## Dashboard Thresholds

In Grafana:

* Green → below 51%
* Yellow → 51% to 79%
* Red → 80% and above

## Cleaning

Basic clean:

```
make clean
```

Full clean:

```
make clean-full
```

Removes contents of:

* logs/
* inputs/
* xdsl\_files/
* dashboards/

## Troubleshooting

* **BN generation fails?**

  Check logs:

  ```
  logs/generate_bn.log
  ```

* **Grafana not starting?**

  Ensure Homebrew Grafana service:

  ```
  brew services start grafana
  ```

* **pysmile import error?**

  Confirm your environment:

  ```
  conda activate midterm_env
  python -c "import pysmile"
  ```

Enjoy your Bayesian monitoring stack!
