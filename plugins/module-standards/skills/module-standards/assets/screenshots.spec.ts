import { expect, test, type Page } from '@playwright/test';

const baseUrl = requireEnv('MAGENTO_BASE_URL');
const adminPath = process.env.MAGENTO_ADMIN_PATH ?? 'admin';
const outputDirectory = process.env.SCREENSHOT_DIR ?? 'docs/images';

const configSections: ReadonlyArray<{ readonly section: string; readonly file: string }> = [
    { section: '__SECTION_ID__', file: 'config-__SECTION_ID__.png' },
];

function requireEnv(name: string): string {
    const value = process.env[name];
    if (value === undefined || value === '') {
        throw new Error(`Set ${name} before running the screenshot spec`);
    }
    return value;
}

async function logIntoAdmin(page: Page): Promise<void> {
    await page.goto(`${baseUrl}/${adminPath}`);
    await page.fill('#username', requireEnv('MAGENTO_ADMIN_USER'));
    await page.fill('#login', requireEnv('MAGENTO_ADMIN_PASSWORD'));
    await page.click('.action-login');
    await expect(page.locator('.page-wrapper')).toBeVisible();
}

async function expandCollapsedGroups(page: Page): Promise<void> {
    const collapsedHeaders = page.locator('.section-config:not(.active) > .admin__collapsible-block > a');
    const count = await collapsedHeaders.count();
    for (let index = 0; index < count; index++) {
        await collapsedHeaders.nth(0).click();
    }
}

test.use({ viewport: { width: 1440, height: 900 } });

for (const { section, file } of configSections) {
    test(`config section ${section}`, async ({ page }) => {
        await logIntoAdmin(page);
        await page.goto(`${baseUrl}/${adminPath}/admin/system_config/edit/section/${section}/`);
        await expandCollapsedGroups(page);

        await page.locator('#config-edit-form').screenshot({ path: `${outputDirectory}/${file}` });
    });
}
