# appcenter - my collection of appcenter scripts
## appcenter-download-latest-release
Script for downloading and installing the latest release from Microsoft App Center.

## appcenter-secrets.json
Settings to work with:
- api_token
- app_secret
- owner_name
- app_name
- distribution_group_name
- distribution_group_id
- download_path
- installer_filetype

Execute --skip-worktree to avoid commiting appcenter secrets.
```
git update-index --skip-worktree appcenter-secrets.json
```

## Microsoft Visual Studio App Center API
Can be found here: https://openapi.appcenter.ms/