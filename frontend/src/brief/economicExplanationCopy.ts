// Conditional wording for existing Overview measures; no classifications or data changes.
export interface ExplanationChannels { economy: string; fed: string; markets: string }
export type ExplanationCopy = {up:ExplanationChannels;down:ExplanationChannels;negative?:ExplanationChannels;variants?:Record<string,Partial<ExplanationChannels>>};
export const explanationCopy: Record<string, ExplanationCopy> = {
  "payroll": {
    "up": {
      "economy": "More job creation can strengthen household income and spending.",
      "fed": "Sustained labor strength may reduce the case for cuts if inflation remains persistent.",
      "markets": "Stronger earnings prospects can support equities, while higher expected rates can weigh on valuations."
    },
    "down": {
      "economy": "Slower hiring can weaken income and consumption growth.",
      "fed": "If weakness persists and inflation eases, the case for cuts may strengthen.",
      "markets": "Lower expected rates may support equities, but weaker growth and profits can work against them."
    }
  },
  "unemployment": {
    "up": {
      "economy": "Higher unemployment can weaken spending; participation changes also affect this rate.",
      "fed": "Persistent labor weakness could strengthen the case for easing if inflation permits.",
      "markets": "Easing expectations may help valuations, while weaker employment can hurt earnings prospects."
    },
    "down": {
      "economy": "Lower unemployment can support incomes, although exits from the labor force can also lower the rate.",
      "fed": "A tighter labor market may support caution about cuts if wage and price pressures persist.",
      "markets": "Resilient demand can support profits, but higher rate expectations may offset that benefit."
    }
  },
  "claims": {
    "up": {
      "economy": "More new benefit claims may indicate more job losses and pressure on household spending.",
      "fed": "A sustained rise could strengthen easing arguments if inflation is also moderating.",
      "markets": "Lower-rate expectations may help valuations, while layoff concerns can weigh on expected profits."
    },
    "down": {
      "economy": "Fewer new claims may indicate labor resilience, but a single week is volatile.",
      "fed": "Labor resilience may reduce the urgency of cuts if price pressures remain elevated.",
      "markets": "Stronger demand prospects may support earnings, while fewer expected cuts can weigh on valuations."
    }
  },
  "jolts": {
    "up": {
      "economy": "More vacancies can indicate stronger labor demand, not more completed hires.",
      "fed": "Persistent labor tightness could support keeping rates higher if inflation remains firm.",
      "markets": "Demand resilience may help earnings, but wage costs and higher expected rates may pressure valuations."
    },
    "down": {
      "economy": "Fewer vacancies can indicate cooling labor demand and less wage pressure, without proving job losses.",
      "fed": "An orderly cooling could support easing arguments if broader labor and inflation data agree.",
      "markets": "Lower wage pressure can help margins; a sharp demand slowdown can instead hurt revenues."
    }
  },
  "wages": {
    "up": {
      "economy": "Average hourly pay rose faster, adding support to earnings per hour worked.",
      "fed": "Wage growth outpacing productivity may sustain price pressure and argue against rapid cuts.",
      "markets": "Faster hourly pay growth may support spending but raise wage pressure on firms' margins."
    },
    "down": {
      "economy": "Average hourly pay still rose, but more slowly, giving spending a smaller potential boost.",
      "fed": "Slower wage growth may ease cost pressure and support cuts if consumer inflation also slows.",
      "markets": "Slower growth in hourly pay may ease pressure on margins, while weaker pay growth can limit consumer sales."
    },
    "negative": {
      "economy": "Average hourly pay fell, reducing earnings per hour worked.",
      "fed": "Falling hourly pay may ease wage pressure; cuts also require evidence from consumer inflation and employment.",
      "markets": "Falling hourly pay can weaken consumer demand; firms' total labor costs also depend on hours and staffing."
    },
    "variants": {
      "turnPositive": {
        "economy": "Average hourly pay returned to growth after the previous month's decline."
      },
      "fromZeroUp": {
        "economy": "Average hourly pay rose after an unchanged month."
      },
      "turnNegative": {
        "economy": "Average hourly pay fell after rising in the previous month, reducing earnings per hour worked."
      },
      "declineEasing": {
        "economy": "Average hourly pay fell less sharply, but earnings per hour still decreased."
      },
      "declineDeepening": {
        "economy": "Average hourly pay fell more sharply, increasing the loss of earnings per hour."
      }
    }
  },
  "cpi": {
    "up": {
      "economy": "Faster consumer price growth reduces purchasing power if incomes do not keep pace.",
      "fed": "Persistently faster consumer price growth strengthens the case for keeping rates high for longer.",
      "markets": "Expectations of higher rates for longer can lift bond yields and weigh on equity valuations."
    },
    "down": {
      "economy": "Consumer prices still rose, but more slowly, reducing the pace of purchasing-power erosion.",
      "fed": "Sustained moderation in consumer price growth can support rate cuts.",
      "markets": "Lower expected rates may reduce bond yields and support equity valuations."
    },
    "variants": {
      "turnPositive": {
        "economy": "Consumer prices rose after the previous decline."
      },
      "fromZeroUp": {
        "economy": "Consumer prices rose after an unchanged month."
      }
    }
  },
  "coreCpi": {
    "up": {
      "economy": "Prices excluding food and energy rose faster, increasing pressure on household purchasing power.",
      "fed": "Persistently faster core price growth may delay cuts, alongside evidence from PCE and employment.",
      "markets": "Expectations of higher rates for longer can lift bond yields and weigh on equity valuations."
    },
    "down": {
      "economy": "Prices excluding food and energy still rose, but more slowly, easing pressure on household budgets.",
      "fed": "Repeated moderation in core prices can support cuts if PCE inflation also slows.",
      "markets": "Lower expected rates may reduce bond yields and support equity valuations."
    },
    "variants": {
      "turnPositive": {
        "economy": "Prices excluding food and energy rose after the previous decline."
      },
      "fromZeroUp": {
        "economy": "Prices excluding food and energy rose after an unchanged month."
      }
    }
  },
  "corePce": {
    "up": {
      "economy": "Core PCE excludes food and energy and helps assess underlying consumer price pressure.",
      "fed": "The Fed tracks core PCE for persistence; sustained pressure can delay cuts. Its 2% goal concerns annual headline PCE.",
      "markets": "Higher expected rates can weigh on valuations, while resilient demand may still support earnings."
    },
    "down": {
      "economy": "Slower monthly core PCE suggests easing underlying pressure, not necessarily lower prices or annual inflation.",
      "fed": "Sustained moderation in core PCE can support cuts. The 2% goal concerns annual headline PCE, not this monthly core rate.",
      "markets": "Lower expected rates can help valuations, but weak demand behind disinflation may hurt earnings."
    }
  },
  "ppi": {
    "up": {
      "economy": "Producer selling prices rose faster, potentially raising prices for buyers without automatically raising CPI.",
      "fed": "PPI adds to inflation concerns if producers' price increases pass through to consumer spending prices.",
      "markets": "Higher selling prices may raise producers' revenues and buyers' costs; margins also depend on production costs."
    },
    "down": {
      "economy": "Producer selling prices still rose, but more slowly, easing the pace of price increases faced by buyers.",
      "fed": "Slower producer price growth can support a softer inflation outlook if consumer price growth also eases.",
      "markets": "Slower selling-price growth may limit producers' revenue growth and ease price pressure on buyers."
    },
    "negative": {
      "economy": "Producer selling prices fell, reducing prices received by producers and paid by their buyers.",
      "fed": "Falling producer selling prices can ease consumer inflation pressure if the reductions pass through.",
      "markets": "Lower selling prices can reduce producers' revenues and buyers' costs; margins depend on how production costs change."
    },
    "variants": {
      "turnPositive": {
        "economy": "Producer selling prices rose after falling in the previous month, increasing prices faced by buyers."
      },
      "fromZeroUp": {
        "economy": "Producer selling prices rose after an unchanged month, increasing prices faced by buyers."
      },
      "turnNegative": {
        "economy": "Producer selling prices fell after the previous increase, reducing prices faced by buyers."
      },
      "declineEasing": {
        "economy": "Producer selling prices fell less sharply; buyers still paid lower prices than in the previous month."
      },
      "declineDeepening": {
        "economy": "Producer selling prices fell more sharply, deepening the price decline faced by buyers."
      }
    }
  },
  "activity": {
    "up": {
      "economy": "Faster real GDP growth means a larger increase in economy-wide output and income.",
      "fed": "Persistent demand strength may argue against rapid cuts if inflation remains elevated.",
      "markets": "Stronger earnings may support equities, while higher rate expectations can offset that support."
    },
    "down": {
      "economy": "Real GDP still grew, but more slowly, giving output and income a smaller increase.",
      "fed": "If weakness persists and inflation eases, a stronger case for easing may emerge.",
      "markets": "Lower expected rates may help valuations, while weaker growth and profits may weigh on prices."
    },
    "negative": {
      "economy": "Real GDP fell, reducing economy-wide output and income.",
      "fed": "Sustained declines in output may support easing if inflation is moderating.",
      "markets": "Falling output can weaken firms' sales and profit expectations."
    },
    "variants": {
      "turnPositive": {
        "economy": "Real GDP returned to growth, expanding economy-wide output after the previous decline."
      },
      "declineEasing": {
        "economy": "Real GDP fell less sharply, but economy-wide output was still contracting."
      },
      "declineDeepening": {
        "economy": "Real GDP fell more sharply, deepening the decline in economy-wide output and income."
      }
    }
  },
  "income": {
    "up": {
      "economy": "Income after tax and inflation grew faster, giving households more funds for consumption and saving.",
      "fed": "If stronger incomes sustain spending and price pressure, they may reduce the case for cuts.",
      "markets": "Stronger real income growth can support sales at consumer-facing firms."
    },
    "down": {
      "economy": "Income after tax and inflation still rose, but more slowly, adding less to households' spending and saving capacity.",
      "fed": "If slower income growth restrains spending and price pressure, it may strengthen the case for easing.",
      "markets": "Slower real income growth may limit sales growth at consumer-facing firms."
    },
    "negative": {
      "economy": "Income after tax and inflation fell, leaving households less current income for consumption and saving.",
      "fed": "If falling incomes restrain spending and price pressure, they strengthen the case for easier policy.",
      "markets": "Lower real incomes may reduce sales at consumer-facing firms."
    },
    "variants": {
      "turnPositive": {
        "economy": "Income after tax and inflation returned to growth, restoring some household spending and saving capacity."
      },
      "fromZeroUp": {
        "economy": "Income after tax and inflation rose after an unchanged month, adding to household spending and saving capacity."
      },
      "turnNegative": {
        "economy": "Income after tax and inflation fell after the previous increase, leaving less for consumption and saving."
      },
      "declineEasing": {
        "economy": "Income after tax and inflation fell less sharply, but households still had less income for consumption and saving."
      },
      "declineDeepening": {
        "economy": "Income after tax and inflation fell more sharply, further reducing funds for consumption and saving."
      }
    }
  },
  "retail": {
    "up": {
      "economy": "Retail sales value grew faster; the measure includes price changes, not just quantities purchased.",
      "fed": "Stronger sales argue against rapid cuts if they reflect rising real demand rather than prices alone.",
      "markets": "Faster sales growth can support retailers' revenue growth."
    },
    "down": {
      "economy": "Retail sales value still rose, but more slowly; it includes price changes, not just quantities purchased.",
      "fed": "Slower sales growth supports easier policy only if it confirms weaker real demand.",
      "markets": "Slower sales growth may limit retailers' revenue growth."
    },
    "negative": {
      "economy": "Retail sales value fell; price changes must be separated before concluding that quantities purchased fell.",
      "fed": "A sales decline supports easing if it confirms weaker real spending and easing price pressure.",
      "markets": "Falling sales value can reduce retailers' revenues."
    },
    "variants": {
      "turnPositive": {
        "economy": "Retail sales value rose after the previous decline; it includes changes in both prices and quantities."
      },
      "fromZeroUp": {
        "economy": "Retail sales value rose after an unchanged month; it includes changes in both prices and quantities."
      },
      "turnNegative": {
        "economy": "Retail sales value fell after the previous increase; changes in prices and quantities both affect the measure."
      },
      "declineEasing": {
        "economy": "Retail sales value fell less sharply, but still decreased; the measure includes price changes."
      },
      "declineDeepening": {
        "economy": "Retail sales value fell more sharply; the measure includes price changes as well as quantities."
      }
    }
  },
  "starts": {
    "up": {
      "economy": "More construction starts can support residential investment, jobs and demand for materials.",
      "fed": "Sustained housing strength may indicate resilient demand, but inflation and employment drive the broader policy decision.",
      "markets": "Builders and suppliers may benefit from demand, while financing costs can limit margins and valuations."
    },
    "down": {
      "economy": "Fewer construction starts can weaken residential investment and demand for building materials.",
      "fed": "Persistent housing weakness may strengthen easing arguments if inflation allows.",
      "markets": "Lower-rate expectations may support valuations, but weaker construction demand can hurt builders and suppliers."
    }
  },
  "permits": {
    "up": {
      "economy": "More permits suggest a stronger project pipeline, but authorization does not guarantee construction.",
      "fed": "A persistent rise may show housing resilience; policy still depends on the broader inflation and labor outlook.",
      "markets": "A stronger pipeline may help builders’ prospects, while financing costs can offset that benefit."
    },
    "down": {
      "economy": "Fewer permits may indicate a weaker future construction pipeline, not an immediate decline in completed homes.",
      "fed": "A sustained decline may support easing arguments if broader demand weakens and inflation permits.",
      "markets": "Easing expectations may help valuations, but a weaker project pipeline can hurt expected revenues."
    }
  },
  "mortgage": {
    "up": {
      "economy": "Higher mortgage rates reduce affordability and can restrain home purchases and construction.",
      "fed": "Tighter financing can cool demand; mortgage rates also reflect bond yields and spreads, not just Fed decisions.",
      "markets": "Housing-sensitive earnings may weaken; mortgage margins and bank effects depend on funding costs as well."
    },
    "down": {
      "economy": "Lower mortgage rates improve affordability and may support housing demand, subject to incomes and credit standards.",
      "fed": "Easier financing can support demand; a mortgage-rate decline does not itself establish a new Fed cut.",
      "markets": "Housing businesses may benefit, but lower rates associated with recession fears can coincide with weaker profits."
    }
  },
  "nfci": {
    "up": {
      "economy": "Tightening financial conditions can constrain borrowing, spending and risk-taking, even while the level remains below zero.",
      "fed": "Broader tightening may reduce the need for additional restraint, depending on inflation and activity.",
      "markets": "Tighter credit can hurt profits and valuations, while lower expected policy rates may provide some support."
    },
    "down": {
      "economy": "Easing financial conditions can support borrowing and demand, even while the level remains above zero.",
      "fed": "Easier financing may sustain demand and reduce the urgency of cuts if inflation remains persistent.",
      "markets": "Easier financing can help valuations and earnings, but may also sustain inflation and higher-rate expectations."
    }
  },
  "curve": {
    "up": {
      "economy": "A wider spread can reflect policy expectations, growth or term premia; it does not identify which yield moved.",
      "fed": "The slope reflects expectations as well as risk premia, not an announced change in policy.",
      "markets": "Short- and long-duration bonds can react differently; a positive spread does not remove recession risk."
    },
    "down": {
      "economy": "A narrower spread can reflect changing policy or growth expectations; inversion alone does not confirm recession.",
      "fed": "A flatter curve does not by itself establish the timing or size of future rate cuts.",
      "markets": "Falling growth expectations may help some bonds but hurt equities; the spread alone does not reveal that mix."
    }
  },
  "consumption": {
    "up": {
      "economy": "Consumers bought more goods and services after adjusting for prices, supporting demand and firms' sales.",
      "fed": "Sustained growth in real consumer spending may argue against rapid cuts if inflation remains elevated.",
      "markets": "Faster real spending growth may support sales growth at consumer-facing firms."
    },
    "down": {
      "economy": "Consumers still bought more after adjusting for prices, but spending growth slowed.",
      "fed": "Persistent slowing in consumer spending can support cuts if price pressure also eases.",
      "markets": "Slower real spending growth may limit sales growth at consumer-facing firms."
    },
    "negative": {
      "economy": "Consumers bought fewer goods and services after adjusting for prices, weakening demand for firms' output.",
      "fed": "A sustained decline in consumer spending can support easing if inflation is moderating.",
      "markets": "Falling real consumer spending may reduce sales at consumer-facing firms."
    },
    "variants": {
      "turnPositive": {
        "economy": "Consumer purchases returned to growth after adjusting for prices, restoring demand for firms' goods and services."
      },
      "declineEasing": {
        "economy": "Consumers bought less after adjusting for prices, but the fall in their spending eased."
      },
      "declineDeepening": {
        "economy": "Real consumer spending fell more sharply, weakening demand for firms' goods and services."
      }
    }
  },
  "manufacturingPmi": {
    "up": {
      "economy": "Manufacturing continued to expand, with a stronger survey signal than last month.",
      "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
      "markets": "Stronger manufacturing expansion may improve expectations for revenue growth in the sector."
    },
    "down": {
      "economy": "Manufacturing continued to expand, but the expansion signal weakened from last month.",
      "fed": "Persistently slower expansion may support cuts if inflation also eases.",
      "markets": "Slower manufacturing expansion may weaken expectations for revenue growth in the sector."
    },
    "variants": {
      "expandingFaster": {
        "economy": "Manufacturing continued to expand, with a stronger survey signal than last month.",
        "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
        "markets": "Stronger manufacturing expansion may improve expectations for revenue growth in the sector."
      },
      "expandingSlower": {
        "economy": "Manufacturing continued to expand, but the expansion signal weakened from last month.",
        "fed": "Persistently slower expansion may support cuts if inflation also eases.",
        "markets": "Slower manufacturing expansion may weaken expectations for revenue growth in the sector."
      },
      "contractingEasing": {
        "economy": "Manufacturing still contracted, but the contraction signal became milder.",
        "fed": "Persistent contraction may support easing if inflation slows, even as the survey decline becomes milder.",
        "markets": "A milder manufacturing contraction may ease concerns about falling sector revenues."
      },
      "contractingDeepening": {
        "economy": "Manufacturing still contracted, with a stronger contraction signal than last month.",
        "fed": "Persistent contraction can strengthen the case for easing if inflation also moderates.",
        "markets": "A deeper manufacturing contraction may weaken sector revenue expectations."
      },
      "atThreshold": {
        "economy": "The manufacturing survey was at 50, indicating no change in sector conditions.",
        "fed": "A PMI of 50 adds no expansion or contraction signal; inflation and employment still guide policy.",
        "markets": "The no-change reading adds no clear directional signal for sector revenue expectations."
      },
      "expansionResumed": {
        "economy": "The manufacturing PMI moved above 50, indicating renewed sector expansion.",
        "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
        "markets": "Stronger manufacturing expansion may improve expectations for revenue growth in the sector."
      },
      "contractionStarted": {
        "economy": "The manufacturing PMI moved below 50, indicating a shift into sector contraction.",
        "fed": "Persistent contraction can strengthen the case for easing if inflation also moderates.",
        "markets": "A deeper manufacturing contraction may weaken sector revenue expectations."
      },
      "expandingUnchanged": {
        "economy": "Manufacturing remained above 50 with an unchanged expansion signal.",
        "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
        "markets": "The unchanged survey signal adds no new change to sector revenue expectations."
      },
      "contractingUnchanged": {
        "economy": "Manufacturing remained below 50 with an unchanged contraction signal.",
        "fed": "Persistent contraction can strengthen the case for easing if inflation also moderates.",
        "markets": "The unchanged survey signal adds no new change to sector revenue expectations."
      }
    }
  },
  "servicesPmi": {
    "up": {
      "economy": "Services continued to expand, with a stronger survey signal than last month.",
      "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
      "markets": "Stronger services expansion may improve expectations for revenue growth in the sector."
    },
    "down": {
      "economy": "Services continued to expand, but the expansion signal weakened from last month.",
      "fed": "Persistently slower expansion may support cuts if inflation also eases.",
      "markets": "Slower services expansion may weaken expectations for revenue growth in the sector."
    },
    "variants": {
      "expandingFaster": {
        "economy": "Services continued to expand, with a stronger survey signal than last month.",
        "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
        "markets": "Stronger services expansion may improve expectations for revenue growth in the sector."
      },
      "expandingSlower": {
        "economy": "Services continued to expand, but the expansion signal weakened from last month.",
        "fed": "Persistently slower expansion may support cuts if inflation also eases.",
        "markets": "Slower services expansion may weaken expectations for revenue growth in the sector."
      },
      "contractingEasing": {
        "economy": "Services still contracted, but the contraction signal became milder.",
        "fed": "Persistent contraction may support easing if inflation slows, even as the survey decline becomes milder.",
        "markets": "A milder services contraction may ease concerns about falling sector revenues."
      },
      "contractingDeepening": {
        "economy": "Services still contracted, with a stronger contraction signal than last month.",
        "fed": "Persistent contraction can strengthen the case for easing if inflation also moderates.",
        "markets": "A deeper services contraction may weaken sector revenue expectations."
      },
      "atThreshold": {
        "economy": "The services survey was at 50, indicating no change in sector conditions.",
        "fed": "A PMI of 50 adds no expansion or contraction signal; inflation and employment still guide policy.",
        "markets": "The no-change reading adds no clear directional signal for sector revenue expectations."
      },
      "expansionResumed": {
        "economy": "The services PMI moved above 50, indicating renewed sector expansion.",
        "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
        "markets": "Stronger services expansion may improve expectations for revenue growth in the sector."
      },
      "contractionStarted": {
        "economy": "The services PMI moved below 50, indicating a shift into sector contraction.",
        "fed": "Persistent contraction can strengthen the case for easing if inflation also moderates.",
        "markets": "A deeper services contraction may weaken sector revenue expectations."
      },
      "expandingUnchanged": {
        "economy": "Services remained above 50 with an unchanged expansion signal.",
        "fed": "Sustained expansion can argue against rapid cuts if inflation remains elevated.",
        "markets": "The unchanged survey signal adds no new change to sector revenue expectations."
      },
      "contractingUnchanged": {
        "economy": "Services remained below 50 with an unchanged contraction signal.",
        "fed": "Persistent contraction can strengthen the case for easing if inflation also moderates.",
        "markets": "The unchanged survey signal adds no new change to sector revenue expectations."
      }
    }
  },
  "production": {
    "up": {
      "economy": "Faster industrial production growth can support orders for inputs and industrial firms' sales.",
      "fed": "Sustained strength in industrial demand may argue against rapid cuts if inflation remains elevated.",
      "markets": "Stronger industrial production may support sales expectations for industrial firms and their suppliers."
    },
    "down": {
      "economy": "Industrial production still grew, but more slowly, giving demand for inputs a smaller boost.",
      "fed": "Persistent slowing in industry may support cuts if consumer inflation also eases.",
      "markets": "Slower production growth may limit sales growth at industrial firms and suppliers."
    },
    "negative": {
      "economy": "Industrial production fell, weakening demand for materials and industrial suppliers' output.",
      "fed": "Persistent declines in industrial production may support easing if inflation slows.",
      "markets": "Falling production may weaken industrial firms' sales and profit expectations."
    },
    "variants": {
      "turnPositive": {
        "economy": "Industrial production returned to growth, restoring demand for materials and suppliers' output."
      },
      "declineEasing": {
        "economy": "Industrial production still fell, but its milder decline reduced the drag on demand for materials."
      }
    }
  }
};

export const flowFacts: Record<string,Record<string,string>> = {
  "average_hourly_earnings": {
    "growingFaster": "Average hourly pay still rose, and its growth rate increased.",
    "growingSlower": "Average hourly pay still rose, but its growth rate slowed.",
    "turnPositive": "Average hourly pay rose after the previous decline.",
    "turnNegative": "Average hourly pay fell after the previous increase.",
    "declineEasing": "Average hourly pay fell less sharply, but was still falling.",
    "declineDeepening": "Average hourly pay fell more sharply.",
    "fromZeroUp": "Average hourly pay rose after an unchanged period.",
    "fromZeroDown": "Average hourly pay fell after an unchanged period.",
    "zero": "Average hourly pay was unchanged at displayed precision."
  },
  "real_consumption": {
    "growingFaster": "Real consumer spending still rose, and its growth rate increased.",
    "growingSlower": "Real consumer spending still rose, but its growth rate slowed.",
    "turnPositive": "Real consumer spending rose after the previous decline.",
    "turnNegative": "Real consumer spending fell after the previous increase.",
    "declineEasing": "Real consumer spending fell less sharply, but was still falling.",
    "declineDeepening": "Real consumer spending fell more sharply.",
    "fromZeroUp": "Real consumer spending rose after an unchanged period.",
    "fromZeroDown": "Real consumer spending fell after an unchanged period.",
    "zero": "Real consumer spending was unchanged at displayed precision."
  },
  "real_disposable_income": {
    "growingFaster": "Real after-tax income still rose, and its growth rate increased.",
    "growingSlower": "Real after-tax income still rose, but its growth rate slowed.",
    "turnPositive": "Real after-tax income rose after the previous decline.",
    "turnNegative": "Real after-tax income fell after the previous increase.",
    "declineEasing": "Real after-tax income fell less sharply, but was still falling.",
    "declineDeepening": "Real after-tax income fell more sharply.",
    "fromZeroUp": "Real after-tax income rose after an unchanged period.",
    "fromZeroDown": "Real after-tax income fell after an unchanged period.",
    "zero": "Real after-tax income was unchanged at displayed precision."
  },
  "retail_sales": {
    "growingFaster": "Nominal retail sales still rose, and its growth rate increased.",
    "growingSlower": "Nominal retail sales still rose, but its growth rate slowed.",
    "turnPositive": "Nominal retail sales rose after the previous decline.",
    "turnNegative": "Nominal retail sales fell after the previous increase.",
    "declineEasing": "Nominal retail sales fell less sharply, but was still falling.",
    "declineDeepening": "Nominal retail sales fell more sharply.",
    "fromZeroUp": "Nominal retail sales rose after an unchanged period.",
    "fromZeroDown": "Nominal retail sales fell after an unchanged period.",
    "zero": "Nominal retail sales was unchanged at displayed precision."
  },
  "real_gdp": {
    "growingFaster": "Real GDP still rose, and its growth rate increased.",
    "growingSlower": "Real GDP still rose, but its growth rate slowed.",
    "turnPositive": "Real GDP rose after the previous decline.",
    "turnNegative": "Real GDP fell after the previous increase.",
    "declineEasing": "Real GDP fell less sharply, but was still falling.",
    "declineDeepening": "Real GDP fell more sharply.",
    "fromZeroUp": "Real GDP rose after an unchanged period.",
    "fromZeroDown": "Real GDP fell after an unchanged period.",
    "zero": "Real GDP was unchanged at displayed precision."
  },
  "payrolls": {
    "growingFaster": "Employment still rose, and its growth rate increased.",
    "growingSlower": "Employment increased, but the monthly gain slowed.",
    "turnPositive": "Employment rose after the previous decline.",
    "turnNegative": "Employment fell after the previous increase.",
    "declineEasing": "Employment fell less sharply, but was still falling.",
    "declineDeepening": "Employment fell more sharply.",
    "fromZeroUp": "Employment rose after an unchanged period.",
    "fromZeroDown": "Employment fell after an unchanged period.",
    "zero": "Employment was unchanged at displayed precision."
  }
};
