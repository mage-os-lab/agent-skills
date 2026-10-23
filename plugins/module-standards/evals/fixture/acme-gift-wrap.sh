#!/usr/bin/env bash
# Builds a released Magento module with known gaps against the Mage-OS standard:
# acme/ vendor, custom config tab, top-level menu, admin controller without ACL,
# a vendor callhome cron, PHPStan at level 2, no CI, no tests, and one real bug
# (Config reads giftwrap/general/enable, the field is giftwrap/general/enabled).
# A previous scorecard declined the rename until the next major release.
set -euo pipefail

mkdir -p etc/adminhtml Model Cron Controller/Adminhtml/Index

cat > composer.json <<'JSON'
{
    "name": "acme/module-gift-wrap",
    "description": "Lets customers add gift wrapping to their order.",
    "type": "magento2-module",
    "license": "OSL-3.0",
    "require": {
        "php": ">=8.1",
        "magento/framework": "^103.0"
    },
    "autoload": {
        "files": ["registration.php"],
        "psr-4": { "Acme\\GiftWrap\\": "" }
    }
}
JSON

cat > registration.php <<'PHP'
<?php
declare(strict_types=1);

use Magento\Framework\Component\ComponentRegistrar;

ComponentRegistrar::register(ComponentRegistrar::MODULE, 'Acme_GiftWrap', __DIR__);
PHP

cat > etc/module.xml <<'XML'
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:framework:Module/etc/module.xsd">
    <module name="Acme_GiftWrap"/>
</config>
XML

cat > etc/acl.xml <<'XML'
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:framework:Acl/etc/acl.xsd">
    <acl>
        <resources>
            <resource id="Magento_Backend::admin">
                <resource id="Acme_GiftWrap::menu" title="Gift Wrap"/>
                <resource id="Magento_Backend::stores">
                    <resource id="Magento_Backend::stores_settings">
                        <resource id="Magento_Config::config">
                            <resource id="Acme_GiftWrap::config" title="Gift Wrap"/>
                        </resource>
                    </resource>
                </resource>
            </resource>
        </resources>
    </acl>
</config>
XML

cat > etc/adminhtml/system.xml <<'XML'
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Config:etc/system_file.xsd">
    <system>
        <tab id="acme" translate="label" sortOrder="10">
            <label>Acme Extensions</label>
        </tab>
        <section id="giftwrap" translate="label" sortOrder="10" showInDefault="1" showInWebsite="1">
            <label>Gift Wrap</label>
            <tab>acme</tab>
            <resource>Acme_GiftWrap::config</resource>
            <group id="general" translate="label" sortOrder="10" showInDefault="1" showInWebsite="1">
                <label>General</label>
                <field id="enabled" translate="label" type="select" sortOrder="10" showInDefault="1" showInWebsite="1">
                    <label>Enabled</label>
                    <source_model>Magento\Config\Model\Config\Source\Yesno</source_model>
                </field>
                <field id="price" translate="label" type="text" sortOrder="20" showInDefault="1" showInWebsite="1">
                    <label>Price</label>
                </field>
            </group>
        </section>
    </system>
</config>
XML

cat > etc/adminhtml/menu.xml <<'XML'
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Backend:etc/menu.xsd">
    <menu>
        <add id="Acme_GiftWrap::menu" title="Acme" module="Acme_GiftWrap" sortOrder="90" resource="Acme_GiftWrap::menu"/>
        <add id="Acme_GiftWrap::overview" title="Gift Wrap Orders" module="Acme_GiftWrap" sortOrder="10" parent="Acme_GiftWrap::menu" action="giftwrap/index/index" resource="Acme_GiftWrap::menu"/>
    </menu>
</config>
XML

cat > etc/crontab.xml <<'XML'
<?xml version="1.0"?>
<config xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="urn:magento:module:Magento_Cron:etc/crontab.xsd">
    <group id="default">
        <job name="acme_giftwrap_ping" instance="Acme\GiftWrap\Cron\Ping" method="execute">
            <schedule>0 3 * * *</schedule>
        </job>
    </group>
</config>
XML

cat > Model/Config.php <<'PHP'
<?php
declare(strict_types=1);

namespace Acme\GiftWrap\Model;

use Magento\Framework\App\Config\ScopeConfigInterface;
use Magento\Store\Model\ScopeInterface;

class Config
{
    public function __construct(private ScopeConfigInterface $scopeConfig)
    {
    }

    public function isEnabled(): bool
    {
        return $this->scopeConfig->isSetFlag('giftwrap/general/enable', ScopeInterface::SCOPE_WEBSITE);
    }

    public function getPrice()
    {
        return $this->scopeConfig->getValue('giftwrap/general/price', ScopeInterface::SCOPE_WEBSITE);
    }
}
PHP

cat > Cron/Ping.php <<'PHP'
<?php
declare(strict_types=1);

namespace Acme\GiftWrap\Cron;

use Magento\Framework\HTTP\Client\Curl;
use Magento\Store\Model\StoreManagerInterface;

class Ping
{
    public function __construct(private Curl $curl, private StoreManagerInterface $storeManager)
    {
    }

    public function execute(): void
    {
        $this->curl->post('https://stats.acme-extensions.example/ping', [
            'domain' => $this->storeManager->getStore()->getBaseUrl(),
            'module' => 'Acme_GiftWrap',
        ]);
    }
}
PHP

cat > Controller/Adminhtml/Index/Index.php <<'PHP'
<?php
declare(strict_types=1);

namespace Acme\GiftWrap\Controller\Adminhtml\Index;

use Magento\Backend\App\Action;
use Magento\Framework\Controller\ResultFactory;

class Index extends Action
{
    public function execute()
    {
        return $this->resultFactory->create(ResultFactory::TYPE_PAGE);
    }
}
PHP

cat > phpstan.neon <<'NEON'
parameters:
    level: 2
    paths:
        - .
    excludePaths:
        - vendor
NEON

cat > LICENSE.txt <<'TXT'
Open Software License ("OSL") v. 3.0
TXT

cat > README.md <<'MD'
# Acme Gift Wrap

Install with composer and enable the module.
MD

cat > .mage-os-standards.json <<'JSON'
{
  "checked_at": "2026-09-01",
  "skill_version": 2,
  "areas": {
    "identity": "fail",
    "license": "pass",
    "integrity": "fail",
    "admin_ux": "fail",
    "ci": "fail",
    "static_analysis": "partial",
    "tests": "fail",
    "security": "fail",
    "documentation": "fail",
    "hygiene": "partial"
  },
  "decisions": {
    "identity.rename": {
      "choice": "declined",
      "date": "2026-09-01",
      "reason": "Agencies pin acme/module-gift-wrap in their composer.json; rename with 2.0",
      "ask_again": "next_major",
      "version_at_decision": "1.4.0"
    }
  },
  "notes": []
}
JSON

git init --quiet
git -c user.name=Fixture -c user.email=fixture@example.com add -A
git -c user.name=Fixture -c user.email=fixture@example.com commit --quiet -m "Release 1.4.0"
git tag v1.4.0
