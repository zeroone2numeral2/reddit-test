from imgurpython import ImgurClient


class Imgur(ImgurClient):
    def __init__(self, *args, **kwargs):
        ImgurClient.__init__(self,  *args, **kwargs)
    
    def get_url(self, image_id):
        return self.get_image(image_id).link
    
    def get_album_urls(self, album_id):
        return [image.link for image in self.get_album_images(album_id)]
    
    
# print(client.get_url('h3SXiil'))
# print(client.get_album_urls('l9A1Z'))
