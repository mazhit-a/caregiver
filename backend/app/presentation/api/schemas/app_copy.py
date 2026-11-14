from app.presentation.api.schemas.base import CamelModel


class NavCopyOut(CamelModel):
    today: str
    plan: str
    profile_page: str
    skills: str
    settings: str


class PlanCopyOut(CamelModel):
    title: str
    subtitle: str
    quick_guides_title: str
    quick_guides_caption: str


class ProfileCopyOut(CamelModel):
    title: str
    privacy_note: str
    works_title: str
    about_title: str
    enjoys_title: str
    calms_title: str
    avoid_title: str
    rhythm_title: str
    contacts_title: str
    empty_phrases: str
    edit_note: str


class CareCardCopyOut(CamelModel):
    title: str
    purpose: str
    sharing_sentence: str


class VisitSheetCopyOut(CamelModel):
    title: str
    subtitle: str


class SkillsCopyOut(CamelModel):
    title: str
    subtitle: str


class SettingsCopyOut(CamelModel):
    title: str
    gentle_exit_entry: str
    gentle_exit_hint: str


class WelcomeCopyOut(CamelModel):
    title: str
    body: str
    name_label: str


class AppCopyResponse(CamelModel):
    nav: NavCopyOut
    plan: PlanCopyOut
    profile: ProfileCopyOut
    care_card: CareCardCopyOut
    visit_sheet: VisitSheetCopyOut
    skills: SkillsCopyOut
    settings: SettingsCopyOut
    welcome: WelcomeCopyOut
