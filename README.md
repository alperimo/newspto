# Crypto News Scrapper

This repository provides tools for scraping cryptocurrency-related news and analyzing the impact of specific events on coin/token prices. Key features include:

**1. Fetching News from CoinMarketCal and Similar Platforms**
- The tool automatically scrapes up-to-date cryptocurrency news from platforms like CoinMarketCal to curate event-specific datasets.

**2. Retrieving Event-Specific Price Data**
- It collects historical price data for coins/tokens related to specific events from multiple exchanges.
- Focuses on capturing price movements before, during, and after the event for detailed analysis.

**3. Automated Q&A Dataset Creation for Fine-Tuning**
- The tool leverages Unsloth for fine-tuning models and generates question-and-answer datasets using OpenAI’s chat-based system.
- These datasets help evaluate and analyze the effects of events on coins/tokens, providing valuable insights for crypto-specific NLP tasks.

### JSONL Format
- Each line represents a single event, containing detailed metadata about the event, related coins/tokens, price movements, and AI-generated analyses.

```json
{
  "id": "xxx-app-listing-192017",
  "category": "Exchange",
  "coins": ["Token (XXX)"],
  "date": "14 Dec 2023",
  "title": "XXX App Listing",
  "description": "No additional information.",
  "coinChangeDollarsOnRetrieve": ["$0.000022"],
  "coinChangePercentsOnRetrieve": ["0.79%"],
  "aiAnalysis": "",
  "proofImage": "data/scrap-outputs/images/1000/xxx-app-listing-192017.png",
  "sourceHref": "https://twitter.com/example/status/123456789",
  "confidencePct": 0.0,
  "votes": 0,
  "coinsPricesByDate": {
    "XXXUSDT": {
      "2023-12-15": [0.0000271725, 0.00002854, 0.0000276975, 0.0000300275],
      "2023-12-16": [0.0000233675, 0.0000239, 0.000024795],
      "2023-12-17": [0.0000218575, 0.000021975, 0.00002196]
    }
  }
}
```

### CSV Format
The CSV format is a simpler, tabular representation of the same data, suitable for quick analysis, visualization, or integration into tools like Excel or pandas. Each row represents an event with summarized data fields.

```csv
Title,Text
"Analyze the following cryptocurrency event: ID: xxx-token-unlock-227888","ID: xxx-token-unlock-227888, Category: Tokenomics event, Date: 07 Oct 2024, Title: XXX Token Unlock, Coins involved: XXX, Description: Unlock of 0.5% circulating supply at 12 AM UTC., Proof image URL: data/scrap-outputs/images/1/xxx-token-unlock-227888.png, Source link: https://example.com/token-unlock, Votes: 32, Forecasted prices: Avoid buying 7 days before and sell 3 days after to prevent -12.23% loss."
```

**Use Cases**
- Fine-tuning language models for cryptocurrency-focused NLP tasks.
- Analyzing the influence of events (e.g., partnership announcements, regulatory updates, product launches) on coin/token prices.
- Creating Q&A datasets for evaluating market trends and sentiment analysis in the crypto domain.
