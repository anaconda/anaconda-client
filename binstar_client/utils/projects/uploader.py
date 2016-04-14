from tempfile import SpooledTemporaryFile
import requests
import binstar_client
from binstar_client.requests_ext import stream_multipart
from binstar_client.utils import compute_hash, jencode


class ProjectUploader(binstar_client.Binstar):
    def __init__(self, token, **kwargs):
        domain = kwargs.get('domain', 'https://api.anaconda.org')
        verify = kwargs.get('verify', True)
        self.username = kwargs.get('username', None)
        self.project = kwargs.get('project', None)
        super(ProjectUploader, self).__init__(token, domain, verify)

    def exists(self):
        url = "{}/apps/{}/project/{}".format(
            self.domain, self.username, self.project.name)
        res = self.session.get(url)
        return res.status_code == 200

    def create(self):
        url = "{}/apps/{}/project".format(self.domain, self.username)
        data, headers = jencode(self.project.to_project_creation())
        res = self.session.post(url, data=data, headers=headers)
        return res

    def stage(self):
        url = "{}/apps/{}/project/{}/stage".format(
            self.domain, self.username, self.project.name)
        data, headers = jencode(self.project.to_stage())
        res = self.session.post(url, data=data, headers=headers)
        return res

    def commit(self, revision_id):
        url = "{}/apps/{}/project/{}/commit".format(
            self.domain, self.username, self.project.name)
        data, headers = jencode({'revision_id': revision_id})
        res = self.session.post(url, data=data, headers=headers)
        return res

    def file_upload(self, url, obj):
        _hexmd5, b64md5, size = compute_hash(
            self.project.tar, size=self.project.size)

        s3data = obj['form_data']
        s3data['Content-Length'] = size
        s3data['Content-MD5'] = b64md5

        data_stream, headers = stream_multipart(
            s3data, files={'file': (self.project.basename, self.project.tar)})

        s3res = requests.post(
            url,
            data=data_stream,
            verify=self.session.verify,
            timeout=10 * 60 * 60,
            headers=headers)

        if s3res.status_code != 201:
            raise binstar_client.errors.BinstarError(
                'Error uploading package', s3res.status_code)
        return s3res

    def projects(self):
        url = "{}/apps/{}/projects".format(self.domain, self.username)
        data, headers = jencode(self.project.to_project_creation())
        return self.session.get(url, data=data, headers=headers)

    def upload(self, labels=['main']):
        '''
        * Check if project already exists
            * if it doesn't, then create it
        * stage a new revision
        * upload
        * commit revision
        '''
        if not self.exists():
            self.create()

        data = self.stage().json()
        self.file_upload(data['post_url'], data)
        res = self.commit(data['form_data']['revision_id'])
        return res.json()
