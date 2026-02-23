# Microsoft Foundry Setup for GitHub Actions

This repository is configured to use **Microsoft Foundry** (Azure Cognitive Services) instead of the direct Anthropic API.

## ✅ Already Configured

- `.claude/settings.json` - Foundry configuration copied from your local setup
- GitHub Actions workflows updated to use Foundry
- Azure CLI installation in workflows

## 🔑 Required: Set Up Azure Credentials

For the workflows to authenticate with Azure Foundry, you need to add Azure credentials as a GitHub secret.

### Option 1: Using Azure CLI (Recommended)

**Step 1: Create a Service Principal**

```bash
# Login to Azure
az login

# Get your subscription ID
az account show --query id -o tsv

# Create a service principal with Contributor role
# Replace YOUR_SUBSCRIPTION_ID with your actual subscription ID
az ad sp create-for-rbac \
  --name "github-actions-foundry" \
  --role Contributor \
  --scopes /subscriptions/YOUR_SUBSCRIPTION_ID \
  --sdk-auth
```

This will output JSON like:
```json
{
  "clientId": "xxxxx",
  "clientSecret": "xxxxx",
  "subscriptionId": "xxxxx",
  "tenantId": "xxxxx",
  ...
}
```

**Step 2: Copy the entire JSON output**

**Step 3: Add to GitHub Secrets**

1. Go to: https://github.com/dngoins/auto-agent/settings/secrets/actions
2. Click "New repository secret"
3. Name: `AZURE_CREDENTIALS`
4. Value: Paste the entire JSON from Step 1
5. Click "Add secret"

### Option 2: Using Federated Identity (More Secure)

If you prefer federated identity (no secrets stored):

1. Follow GitHub's guide: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-azure

2. Update the workflows to use:
   ```yaml
   - name: Azure Login
     uses: azure/login@v1
     with:
       client-id: ${{ secrets.AZURE_CLIENT_ID }}
       tenant-id: ${{ secrets.AZURE_TENANT_ID }}
       subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
   ```

### Option 3: Use Your Current Azure Session

If you're already authenticated locally:

```bash
# Check current authentication
az account show

# Get credentials for GitHub
az ad sp create-for-rbac --sdk-auth
```

## 🧪 Testing the Setup

After adding the secret:

1. **Trigger the workflow manually:**
   ```bash
   gh workflow run feature-development.yml \
     -f requirements="Feature: Test\n  Scenario: Test foundry\n    Given foundry is configured\n    Then it should work"
   ```

2. **Or push a .gherkin file:**
   ```bash
   # Make sure you're on a feature branch
   git checkout -b test/foundry-test

   echo "Feature: Test
     Scenario: Test
       Given it works
       Then success" > features/test.gherkin

   git add features/test.gherkin
   git commit -m "Test Foundry setup"
   git push origin test/foundry-test
   ```

3. **Check the workflow:**
   ```bash
   gh run list --limit 1
   gh run watch
   ```

## 🔍 Verifying Configuration

The workflow will:

1. ✅ Install Azure CLI
2. ✅ Login with `AZURE_CREDENTIALS`
3. ✅ Copy `.claude/settings.json` to `~/.claude/`
4. ✅ Claude CLI will use Foundry resource: `azcogsvc-octo-rnd-r4l7`
5. ✅ Make API calls through Azure instead of direct Anthropic

## 🐛 Troubleshooting

### "Azure Login failed"

- Verify `AZURE_CREDENTIALS` secret is set correctly
- Check the service principal has access to the Foundry resource
- Ensure subscription ID is correct

### "Claude CLI error"

- Check `.claude/settings.json` is being copied
- Verify the Foundry resource name is correct: `azcogsvc-octo-rnd-r4l7`
- Check Azure authentication succeeded

### "Permission denied"

The service principal needs access to:
- The Azure Cognitive Services resource
- Sufficient permissions to use the Foundry API

Grant access:
```bash
# Get the service principal object ID
SP_ID=$(az ad sp list --display-name "github-actions-foundry" --query "[0].id" -o tsv)

# Grant Cognitive Services User role
az role assignment create \
  --assignee $SP_ID \
  --role "Cognitive Services User" \
  --scope /subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/YOUR_RESOURCE_GROUP/providers/Microsoft.CognitiveServices/accounts/azcogsvc-octo-rnd-r4l7
```

## 📚 Current Foundry Configuration

From `.claude/settings.json`:

```json
{
  "env": {
    "CLAUDE_CODE_USE_FOUNDRY": "1",
    "ANTHROPIC_FOUNDRY_RESOURCE": "azcogsvc-octo-rnd-r4l7",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "claude-sonnet-4-5",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "claude-haiku-4-5",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "claude-opus-4-6"
  }
}
```

## 🔄 Updating Configuration

If your Foundry resource changes:

1. Update `.claude/settings.json`
2. Commit and push
3. Workflows will automatically use new config

## ✅ Once Configured

After setup is complete:

- ✅ No need for `ANTHROPIC_API_KEY`
- ✅ Uses your Azure Foundry resource
- ✅ All API calls go through Azure
- ✅ Same models available (Sonnet 4.5, Haiku 4.5, Opus 4.6)
- ✅ Billing through Azure, not Anthropic

## 🎯 Next Steps

1. Add `AZURE_CREDENTIALS` secret (see above)
2. Test with a simple feature
3. Monitor workflow runs
4. Check Azure billing/usage

Questions? Check the logs:
```bash
gh run view <run-id> --log
```
