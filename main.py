from core.website import Website

if __name__ == "__main__":
    website = Website("https://www.guardicore.com")
    website_status = website.get_status().to_json(indent=4, sort_keys=True)
    print(website_status)
