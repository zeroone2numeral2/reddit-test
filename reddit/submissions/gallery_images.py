class GalleryImages:
    def __init__(self):
        pass

    @staticmethod
    def test(submission):
        if not hasattr(submission, 'gallery_data'):
            return False

        for media_id, media_metadata in submission.media_metadata.items():
            if media_metadata['e'] != 'Image':
                # if even a single media is not an image, the test fails
                return False

        return True
