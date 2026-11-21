import { db } from "@/db";
import { sql } from "drizzle-orm";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  await db.execute(sql`select 1`);

  return (
    <main dir="rtl" className="grid min-h-screen place-items-center px-6 py-12">
      <section className="w-full max-w-2xl rounded-3xl bg-white p-10 shadow-[0_24px_60px_rgba(16,24,40,0.12)]">
        <h1 className="m-0 text-3xl font-semibold text-slate-950">ربات یانگزی 👽 (نسخه آپدیت‌شده)</h1>
        <ul className="mt-6 list-disc space-y-2 pr-6 text-base text-slate-700">
          <li>دسته جدید «مخدر ها 💊» زیر «نوشیدنی و مشروبات 🥃» در فروشگاه</li>
          <li>ایموجی برای همه دکمه‌های خشک</li>
          <li>مدیریت دکمه‌ها در پنل: مخفی، حذف، تغییر نام، تغییر متن</li>
          <li>راهنمای شیشه‌ای: داف | مواد | رت | بالاخواه | برگشت</li>
        </ul>
        <a
          href="/bot.py"
          download
          className="mt-8 inline-block rounded-xl bg-slate-950 px-6 py-3 text-white"
        >
          ⬇️ دانلود bot.py
        </a>
      </section>
    </main>
  );
}
