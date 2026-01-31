# Odoo Marketplace Upload Checklist for ads_sync Module

This checklist outlines the steps required to upload the `ads_sync` module to the Odoo Marketplace. The module provides Meta (Facebook) Ads synchronization functionality and follows a subscription-based pricing model where installation is free, but ongoing usage requires an active subscription.

## Module Preparation

- [ ] **Manifest File**: Ensure `__manifest__.py` is complete with:
  - Module name, version, description
  - Dependencies listed correctly
  - Author information
  - License details
  - Category classification
  - Website URL

- [ ] **Code Quality**: 
  - [ ] All Python files follow Odoo coding standards
  - [ ] No syntax errors or linting issues
  - [ ] Proper error handling implemented
  - [ ] Security best practices followed

- [ ] **Documentation**:
  - [ ] Technical documentation in `docs/tech_eng.md` and `docs/tech_vi.md`
  - [ ] Non-technical documentation in `docs/nontech_eng.md` and `docs/nontech_vi.md`
  - [ ] Installation instructions included
  - [ ] Configuration guide provided
  - [ ] API documentation if applicable

- [ ] **Testing**:
  - [ ] Unit tests created and passing
  - [ ] Integration tests completed
  - [ ] Manual testing in different Odoo versions
  - [ ] Cross-browser compatibility verified

## Packaging

- [ ] **Module Structure**: Verify all required files are present:
  - [ ] `__init__.py` files in all directories
  - [ ] Models, views, controllers properly organized
  - [ ] Static files and assets included
  - [ ] Security configurations
  - [ ] Data files for initial setup

- [ ] **Dependencies**: 
  - [ ] All required Python packages listed
  - [ ] Odoo version compatibility specified
  - [ ] External service dependencies documented

- [ ] **ZIP Package**: Create a clean ZIP file containing only the module directory (no parent directories)

## Marketplace Submission

- [ ] **Odoo Account**: 
  - [ ] Valid Odoo partner account created
  - [ ] Publisher profile completed
  - [ ] Company information verified

- [ ] **Module Upload**:
  - [ ] Access Odoo Marketplace developer portal
  - [ ] Upload the module ZIP package
  - [ ] Verify upload success

- [ ] **Module Details**:
  - [ ] Title and description (English and supported languages)
  - [ ] Screenshots or demo images
  - [ ] Video demonstration (optional but recommended)
  - [ ] Supported Odoo versions
  - [ ] Module category selection

## Pricing Configuration

- [ ] **Pricing Model**: Set as "Free" for installation
- [ ] **Subscription Setup**:
  - [ ] Configure subscription tiers (if applicable)
  - [ ] Set subscription pricing
  - [ ] Define billing intervals (monthly/yearly)
  - [ ] Specify trial period (if offered)

- [ ] **License Terms**:
  - [ ] Subscription agreement drafted
  - [ ] Refund policy defined
  - [ ] Usage limitations documented
  - [ ] Expiration handling explained

## Legal and Compliance

- [ ] **Intellectual Property**:
  - [ ] All code is original or properly licensed
  - [ ] Third-party components have appropriate licenses
  - [ ] No copyrighted material included

- [ ] **Data Privacy**:
  - [ ] GDPR compliance verified
  - [ ] Data handling policies documented
  - [ ] User consent mechanisms implemented

- [ ] **Terms of Service**:
  - [ ] Marketplace terms accepted
  - [ ] Module-specific terms prepared

## Post-Upload Tasks

- [ ] **Testing in Marketplace**:
  - [ ] Test installation from marketplace
  - [ ] Verify subscription activation flow
  - [ ] Test expiration handling

- [ ] **Marketing Materials**:
  - [ ] Feature highlights prepared
  - [ ] Customer testimonials (if available)
  - [ ] Case studies documented

- [ ] **Support Setup**:
  - [ ] Support contact information provided
  - [ ] FAQ section created
  - [ ] Troubleshooting guide available

## Final Review

- [ ] **Quality Assurance**:
  - [ ] Peer review completed
  - [ ] Final testing in clean environment
  - [ ] Documentation review

- [ ] **Go-Live Checklist**:
  - [ ] All checklist items completed
  - [ ] Backup of final module version created
  - [ ] Emergency rollback plan prepared

---

**Note**: The subscription-based pricing model requires careful implementation of license validation within the module code to prevent usage when subscriptions are expired or not registered. Ensure the module includes proper license checking mechanisms in the controllers and models.