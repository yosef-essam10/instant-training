USE AirbnbProject;
GO

IF OBJECT_ID('dbo.Fact_Listings', 'U') IS NOT NULL DROP TABLE dbo.Fact_Listings;
IF OBJECT_ID('dbo.Dim_Location', 'U') IS NOT NULL DROP TABLE dbo.Dim_Location;
IF OBJECT_ID('dbo.Dim_Host', 'U') IS NOT NULL DROP TABLE dbo.Dim_Host;
IF OBJECT_ID('dbo.Dim_Property', 'U') IS NOT NULL DROP TABLE dbo.Dim_Property;
IF OBJECT_ID('dbo.Dim_Date', 'U') IS NOT NULL DROP TABLE dbo.Dim_Date;
GO

CREATE TABLE dbo.Dim_Location (
    location_key INT IDENTITY(1,1) PRIMARY KEY,
    city NVARCHAR(100) NOT NULL,
    country NVARCHAR(100) NOT NULL
);
GO

CREATE TABLE dbo.Dim_Host (
    host_key INT IDENTITY(1,1) PRIMARY KEY,
    host_name NVARCHAR(200) NOT NULL,
    is_superhost BIT NOT NULL
);
GO

CREATE TABLE dbo.Dim_Property (
    property_key INT IDENTITY(1,1) PRIMARY KEY,
    property_category NVARCHAR(50) NOT NULL,
    bedrooms INT NOT NULL,
    beds INT NOT NULL,
    baths DECIMAL(4,1) NOT NULL,
    guests INT NOT NULL
);
GO

CREATE TABLE dbo.Dim_Date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL,
    day_num INT NOT NULL,
    month_num INT NOT NULL,
    year_num INT NOT NULL
);
GO

CREATE TABLE dbo.Fact_Listings (
    listing_key INT IDENTITY(1,1) PRIMARY KEY,
    location_key INT NOT NULL FOREIGN KEY REFERENCES dbo.Dim_Location(location_key),
    host_key INT NOT NULL FOREIGN KEY REFERENCES dbo.Dim_Host(host_key),
    property_key INT NOT NULL FOREIGN KEY REFERENCES dbo.Dim_Property(property_key),
    date_key INT NOT NULL FOREIGN KEY REFERENCES dbo.Dim_Date(date_key),
    listing_name NVARCHAR(500) NULL,
    price_eur DECIMAL(10,2) NOT NULL,
    is_price_imputed BIT NOT NULL,
    rating DECIMAL(3,2) NULL,
    reviews INT NOT NULL,
    is_guest_favorite BIT NOT NULL,
    is_new_listing BIT NOT NULL,
    url NVARCHAR(1000) NULL
);
GO

INSERT INTO dbo.Dim_Location (city, country)
SELECT DISTINCT city, country
FROM dbo.stg_airbnb;
GO

INSERT INTO dbo.Dim_Host (host_name, is_superhost)
SELECT host_name, MAX(CAST(is_superhost AS INT))
FROM dbo.stg_airbnb
GROUP BY host_name;
GO

INSERT INTO dbo.Dim_Property (property_category, bedrooms, beds, baths, guests)
SELECT DISTINCT property_category, bedrooms, beds, baths, guests
FROM dbo.stg_airbnb;
GO

INSERT INTO dbo.Dim_Date (date_key, full_date, day_num, month_num, year_num)
SELECT DISTINCT
    CAST(FORMAT(scrape_date, 'yyyyMMdd') AS INT),
    scrape_date,
    DAY(scrape_date),
    MONTH(scrape_date),
    YEAR(scrape_date)
FROM dbo.stg_airbnb;
GO

INSERT INTO dbo.Fact_Listings (
    location_key, host_key, property_key, date_key,
    listing_name, price_eur, is_price_imputed, rating, reviews,
    is_guest_favorite, is_new_listing, url
)
SELECT
    dl.location_key,
    dh.host_key,
    dp.property_key,
    dd.date_key,
    s.listing_name,
    s.price_eur,
    s.is_price_imputed,
    s.rating,
    s.reviews,
    s.is_guest_favorite,
    s.is_new_listing,
    s.url
FROM dbo.stg_airbnb s
JOIN dbo.Dim_Location dl ON s.city = dl.city AND s.country = dl.country
JOIN dbo.Dim_Host dh ON s.host_name = dh.host_name
JOIN dbo.Dim_Property dp
    ON s.property_category = dp.property_category
    AND s.bedrooms = dp.bedrooms
    AND s.beds = dp.beds
    AND s.baths = dp.baths
    AND s.guests = dp.guests
JOIN dbo.Dim_Date dd ON CAST(FORMAT(s.scrape_date, 'yyyyMMdd') AS INT) = dd.date_key;
GO

SELECT 'Dim_Location' AS tbl, COUNT(*) AS row_count FROM dbo.Dim_Location
UNION ALL SELECT 'Dim_Host', COUNT(*) FROM dbo.Dim_Host
UNION ALL SELECT 'Dim_Property', COUNT(*) FROM dbo.Dim_Property
UNION ALL SELECT 'Dim_Date', COUNT(*) FROM dbo.Dim_Date
UNION ALL SELECT 'Fact_Listings', COUNT(*) FROM dbo.Fact_Listings;
GO
