## Introduction

This is a **Python Function App** hosted on an **App Service Plan** with an Azure function that performs two operations: **move blog content (posts and blog settings) from staging instance to production instance** and **delete all posts** on a given ghost instance. This function is provisioned as part of a ghost blog deployment on Azure. See details here: https://github.com/achechen/ghost-on-azure-vm

## Standalone Deployment

If you already have two ghost instances (production and staging) and want to provision this function app on its own, you can do so. In that case you need a Python Function App hosted on a Linux App Service Plan. Either fork this repository or use it directly on your Function App as code source. You also need to create the following **app settings**:

- **GHOST_STAGING_URL**: Your staging ghost instance url. Example: **http://staging_mysite.local**
- **GHOST_PROD_URL**: Your production ghost instance url. Example: **http://mysite.local**
- **GHOST_PROD_USERNAME**: Production ghost instance administrator e-mail address. Example: **john@example.com**
- **GHOST_PROD_PASSWORD**: Production ghost instance administrator password.
- **GHOST_STAGING_USERNAME**: Staging ghost instance administrator e-mail address. Example: **john@example.com** 
- **GHOST_STAGING_PASSWORD**: Staging ghost instance administrator password.