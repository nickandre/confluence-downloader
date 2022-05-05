# confluence-downloader

(C) Nick Andre 2022

*Released uner the MIT license to help the other poor saps lacking confluence export.*

**Quick script to download confluence documents and save them to S3.**

After a support ticket some number of months ago where Confluence couldn't restore a deleted space due to their "microservice architecture," I implemented a quick and dirty custom backup script in Python. The goal here is to cache the data externally enabling availability during a disaster (ha).

If you run it on AWS will give you exports of every single page on confluence to S3. Each file will be written to `{space_id}.{page_id}.{version_id}` and it will continue to add any new versions that are marked "current" in the API.

Basically it's dumping the page metadata along with the 'storage' format from Confluence's API; my recollection was you could also opt to export in "display" format which would be a more standard HTML compatible with a custom lambda web app. It's obviously nowhere near as good as a real full export feature but after that original ticket we were concerned about future issues with confluence's backup restore (turned out to be prescient), and in a pinch this would be enough to at least reconstruct the text. There are attachment export features as well but I didn't implement any of it.

This ain't pretty but it works. This is set up to use urllib3 instead of requests since it's native to Lambda runtime.

## Requirements

- S3 bucket
- Lambda function
- IAM Policy on Lambda granting full access to S3
- Cloudwatch trigger to run every few hours
- Admin confluence account, tenant url, and bucket name should be specified in Lambda python code
- You should probably use secrets manager or a better auth scheme than basic, but we needed this quickly

This has been chugging along without much todo for a while. Have not tested any restore yet though believe it wouldn't be too painful. This was created 
