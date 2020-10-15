## Possible imgur urls

Imgur urls are CASE SENSITIVE

### Galleries

- imgur.com/gallery/ (catched by `ImgurGallery`)
- imgur.com/a/ (catched by `ImgurGallery`)

Examples:
- /a/ with just pictures: https://imgur.com/a/6E7hHKh
- /gallery/ with 1 `.mp4` video: https://imgur.com/gallery/dFBBGWu, https://imgur.com/gallery/rT5PKlh
- /gallery/ with 1 `.gif`: https://imgur.com/gallery/Pn6CgRc (direct urls: https://i.imgur.com/gja4XBrh.gif shows just a static picture, but https://i.imgur.com/gja4XBr.gif shows it as a video? (missing final "h"))

### Non-direct urls

Urls that must be parsed by the api to know their type

Examples:
- gifv: https://imgur.com/Qg4e5hI (catched by `ImgurNonDirectUrlVideo`)
- jpg: https://imgur.com/h3SXiil (catched by `ImgurNonDirectUrlImage`)


### Direct urls

Examples:
- to a gifv: https://i.imgur.com/Qg4e5hI.gifv (catched by `Gif`)
- to an image: https://i.imgur.com/h3SXiil.png (catched by `Image`)
- to an mp4: https://i.imgur.com/0JBStvt.mp4 (catched by `Video`)

