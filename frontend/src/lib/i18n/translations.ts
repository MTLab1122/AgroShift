export type SupportedLocale = "en" | "ur" | "ps";

export interface TranslationDictionary {
  appName: string;
  tagline: string;
  module01Title: string;
  nav: {
    dashboard: string;
    farms: string;
    registerFarm: string;
    climateEngine: string;
  };
  languages: {
    en: string;
    ur: string;
    ps: string;
  };
  farmStatus: {
    registered: string;
    coordinates: string;
    area: string;
    hectares: string;
  };
}

export const translations: Record<SupportedLocale, TranslationDictionary> = {
  en: {
    appName: "AgroShift",
    tagline: "NASA Earth Observation & Decision Support Engine",
    module01Title: "Farm Management & Location Intelligence",
    nav: {
      dashboard: "Dashboard",
      farms: "Farms",
      registerFarm: "Register New Farm",
      climateEngine: "Climate Engine (Module 02)",
    },
    languages: {
      en: "English",
      ur: "اردو (Urdu)",
      ps: "پښتو (Pashto)",
    },
    farmStatus: {
      registered: "Registered Farms",
      coordinates: "Coordinates",
      area: "Area",
      hectares: "ha",
    },
  },
  ur: {
    appName: "ایگرو شفٹ",
    tagline: "ناسا ارتھ آبزرویشن اور زرعی فیصلہ ساز انجن",
    module01Title: "فارم مینجمنٹ اور لوکیشن انٹیلیجنس",
    nav: {
      dashboard: "ڈیش بورڈ",
      farms: "فارمز",
      registerFarm: "نیا فارم رجسٹر کریں",
      climateEngine: "موسمیاتی انجن (ماڈیول 02)",
    },
    languages: {
      en: "English",
      ur: "اردو",
      ps: "پښتو",
    },
    farmStatus: {
      registered: "رجسٹرڈ فارمز",
      coordinates: "نقشہ کے کوآرڈینیٹس",
      area: "رقبہ",
      hectares: "ہیکٹر",
    },
  },
  ps: {
    appName: "اېګرو شفټ",
    tagline: "د ناسا د ځمکې کتنې او کرنیزې پرېکړې انجن",
    module01Title: "د فارم مدیریت او د موقعیت مالومات",
    nav: {
      dashboard: "ډشبورډ",
      farms: "فارمونه",
      registerFarm: "نوی فارم ثبت کړئ",
      climateEngine: "د اقلیم انجن (ماډیول 02)",
    },
    languages: {
      en: "English",
      ur: "اردو",
      ps: "پښتو",
    },
    farmStatus: {
      registered: "ثبت شوي فارمونه",
      coordinates: "همغږي (کوآرډینیټس)",
      area: "ساحه",
      hectares: "هکتاره",
    },
  },
};
